"""Administrator enrollment, cohort preview, faculty-scoped visibility and export."""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session, joinedload

from app import database, models, schemas
from app.routes.auth import get_current_user, require_roles
from app.services import course_enrollments as service

router = APIRouter(prefix="/admin/courses", tags=["Course Enrollments"])
_admin = require_roles("admin")


def _course_or_404(db, course_id, *, published=False):
    course = service.published_course(db, course_id) if published else db.query(models.Course).filter_by(id=course_id).first()
    if not course:
        raise HTTPException(404, "Published course not found" if published else "Course not found")
    return course


def _cohort(payload, db):
    if not payload.academic_program and payload.present_year is None and not payload.student_ids:
        raise HTTPException(422, "Select an academic programme, present year, or specific students")
    return service.eligible_students(db, academic_program=payload.academic_program, present_year=payload.present_year, student_ids=payload.student_ids)


@router.get("/{course_id}/enrollments/programmes")
def academic_programmes(course_id: int, db: Session = Depends(database.get_db), _: models.User = Depends(_admin)):
    """Return programme names from Student Master, without exposing student data."""
    _course_or_404(db, course_id)
    rows = db.query(models.User.academic_program).filter(
        models.User.role == "student",
        models.User.academic_program.isnot(None),
    ).distinct().all()
    programmes = sorted({value.strip() for (value,) in rows if value and value.strip()}, key=str.casefold)
    return {"academic_programmes": programmes}


@router.post("/{course_id}/enrollments/preview")
def preview(course_id: int, payload: schemas.EnrollmentCohortRequest, db: Session = Depends(database.get_db), _: models.User = Depends(_admin)):
    _course_or_404(db, course_id)
    students = _cohort(payload, db)
    existing = {row.student_id: row for row in db.query(models.StudentCourseEnrollment).filter(models.StudentCourseEnrollment.course_id == course_id, models.StudentCourseEnrollment.student_id.in_([s.id for s in students] or [-1])).all()}
    items = [{"student_id": s.id, "roll_number": s.roll_number, "name": s.name, "academic_program": s.academic_program, "present_year": s.present_year, "college": s.college, "enrollment_status": existing[s.id].status if s.id in existing else None, "eligible": s.id not in existing} for s in students]
    return {"items": items, "summary": {"matched": len(items), "ready": sum(i["eligible"] for i in items), "already_enrolled": sum(not i["eligible"] for i in items)}}


@router.post("/{course_id}/enrollments/bulk")
def bulk_enroll(course_id: int, payload: schemas.EnrollmentBulkRequest, db: Session = Depends(database.get_db), actor: models.User = Depends(_admin)):
    course = db.query(models.Course).filter_by(id=course_id).with_for_update().first()
    if not course:
        raise HTTPException(404, "Course not found")
    target_status = service.assignment_status(course)
    students = _cohort(payload, db)
    existing = {row.student_id: row for row in db.query(models.StudentCourseEnrollment).filter(models.StudentCourseEnrollment.course_id == course_id, models.StudentCourseEnrollment.student_id.in_([s.id for s in students] or [-1])).all()}
    created, reenrolled, skipped = [], [], []
    for student in students:
        row = existing.get(student.id)
        if row:
            if payload.reenroll_existing and row.status in {"WITHDRAWN", "SUSPENDED", "COMPLETED"}:
                row.status, row.enrollment_source, row.enrolled_by = target_status, "ADMIN", actor.id
                reenrolled.append(student.id)
            else:
                skipped.append(student.id)
            continue
        row = models.StudentCourseEnrollment(student_id=student.id, course_id=course_id, status=target_status, enrollment_source="ADMIN", enrolled_by=actor.id)
        db.add(row); created.append(student.id)
    db.add(models.AdminAuditLog(actor_user_id=actor.id, action="course.enrollment.bulk", target_type="course", target_id=course_id, summary=f"Bulk enrollment processed for {course.title}", details={"status": target_status, "filters": {"academic_program": payload.academic_program, "present_year": payload.present_year}, "created": created, "reenrolled": reenrolled, "skipped": skipped, "reason": payload.reason}))
    db.commit()
    return {"status": target_status, "created": len(created), "reenrolled": len(reenrolled), "skipped": len(skipped), "created_student_ids": created, "reenrolled_student_ids": reenrolled, "skipped_student_ids": skipped}


@router.get("/{course_id}/enrollments")
def list_enrollments(course_id: int, status: str | None = Query(None), search: str | None = Query(None), db: Session = Depends(database.get_db), actor: models.User = Depends(get_current_user)):
    _course_or_404(db, course_id)
    role = (actor.role or "").lower()
    if role not in {"admin", "super_admin"} and not (role == "faculty" and service.faculty_can_view(db, actor.id, course_id)):
        raise HTTPException(403, "Enrollment visibility is restricted to assigned academic faculty")
    query = db.query(models.StudentCourseEnrollment).options(joinedload(models.StudentCourseEnrollment.student)).filter_by(course_id=course_id)
    if status: query = query.filter(models.StudentCourseEnrollment.status == status.upper())
    if search:
        term = f"%{search.strip()}%"
        query = query.join(models.User).filter((models.User.name.ilike(term)) | (models.User.roll_number.ilike(term)))
    rows = query.order_by(models.StudentCourseEnrollment.enrolled_at.desc()).all()
    return {"items": [service.row_payload(row) for row in rows], "total": len(rows)}


@router.patch("/{course_id}/enrollments/{enrollment_id}")
def update_status(course_id: int, enrollment_id: int, payload: schemas.EnrollmentStatusRequest, db: Session = Depends(database.get_db), actor: models.User = Depends(_admin)):
    course = db.query(models.Course).filter_by(id=course_id).with_for_update().first()
    if not course:
        raise HTTPException(404, "Course not found")
    row = db.query(models.StudentCourseEnrollment).filter_by(id=enrollment_id, course_id=course_id).first()
    if not row: raise HTTPException(404, "Enrollment not found")
    if payload.status in {"ACTIVE", "PENDING_ACTIVATION"}:
        if service.assignment_status(course) != payload.status:
            raise HTTPException(409, "Enrollment status must match course availability; publish before activation")
        if not service.student_eligible(row.student):
            raise HTTPException(409, "Student master is not eligible for enrollment")
    if row.status == "PENDING_ACTIVATION" and payload.status == "COMPLETED":
        raise HTTPException(409, "A pending assignment cannot be marked completed")
    previous = row.status; row.status = payload.status
    db.add(models.AdminAuditLog(actor_user_id=actor.id, action="course.enrollment.status_changed", target_type="course_enrollment", target_id=row.id, summary=f"Enrollment changed from {previous} to {row.status}", details={"course_id": course_id, "student_id": row.student_id, "reason": payload.reason}))
    db.commit(); return service.row_payload(row)


@router.get("/{course_id}/enrollments/export.csv")
def export(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_admin)):
    course = _course_or_404(db, course_id)
    rows = db.query(models.StudentCourseEnrollment).options(joinedload(models.StudentCourseEnrollment.student)).filter_by(course_id=course_id).order_by(models.StudentCourseEnrollment.id).all()
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["SYS — Strengthen Your Skills", "Course Enrollment Report"]); writer.writerow(["Course", course.title]); writer.writerow([])
    writer.writerow(["Roll Number", "Student Name", "Academic Programme", "Present Year", "College", "Enrollment Status", "Source", "Enrolled At"])
    for row in rows:
        item = service.row_payload(row); writer.writerow([item["roll_number"], item["student_name"], item["academic_program"], item["present_year"], item["college"], item["status"], item["source"], item["enrolled_at"]])
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="SYS_course_{course_id}_enrollments.csv"'})
