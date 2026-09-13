"""Professional course-enrollment cohort selection and lifecycle operations."""
from sqlalchemy import func, or_
from fastapi import HTTPException
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app import models

STATUSES = {"PENDING_ACTIVATION", "ACTIVE", "COMPLETED", "WITHDRAWN", "SUSPENDED"}


def assignment_status(course):
    if course.publication_status in {"DRAFT", "READY_FOR_REVIEW"}:
        return "PENDING_ACTIVATION"
    if course.publication_status == "PUBLISHED" and course.is_active:
        return "ACTIVE"
    raise HTTPException(409, "Archived or unavailable courses do not accept assignments")


def student_eligible(student):
    return bool(student and (student.role or "").lower() == "student" and student.is_active
                and (student.academic_status or "ACTIVE").upper() == "ACTIVE")


def has_learning_access(db, student_id, course_id):
    return db.query(models.StudentCourseEnrollment.id).join(models.Course).join(
        models.User, models.User.id == models.StudentCourseEnrollment.student_id
    ).filter(
        models.StudentCourseEnrollment.student_id == student_id,
        models.StudentCourseEnrollment.course_id == course_id,
        models.StudentCourseEnrollment.status == "ACTIVE",
        models.Course.publication_status.in_(("PUBLISHED", "PILOT_PUBLISHED")),
        models.Course.is_active.is_(True),
        models.User.is_active.is_(True), func.lower(models.User.role) == "student",
        or_(models.User.academic_status.is_(None), func.upper(models.User.academic_status) == "ACTIVE"),
    ).first() is not None


def activate_pending(db, course, actor):
    """Caller holds the course lock and commits publication plus activation atomically."""
    if assignment_status(course) != "ACTIVE":
        raise HTTPException(409, "Publish the course before activating assignments")
    rows = db.query(models.StudentCourseEnrollment).filter_by(
        course_id=course.id, status="PENDING_ACTIVATION"
    ).with_for_update().all()
    activated, skipped = [], []
    for row in rows:
        if not student_eligible(row.student):
            skipped.append(row.student_id)
            continue
        row.status = "ACTIVE"
        row.updated_at = datetime.now(timezone.utc)
        activated.append(row.student_id)
    result = {"activated": len(activated), "skipped": len(skipped),
              "activated_student_ids": activated, "skipped_student_ids": skipped}
    db.add(models.AdminAuditLog(actor_user_id=actor.id, action="course.enrollment.activate_pending",
        target_type="course", target_id=course.id, summary=f"Activated {len(activated)} pending assignments",
        details={**result, "skip_reason": "Student master is no longer eligible"}))
    return result


def published_course(db: Session, course_id: int):
    return db.query(models.Course).filter(
        models.Course.id == course_id,
        models.Course.is_active.is_(True),
        models.Course.publication_status == "PUBLISHED",
    ).first()


def eligible_students(db: Session, *, academic_program=None, present_year=None, student_ids=None):
    query = db.query(models.User).filter(
        func.lower(models.User.role) == "student",
        models.User.is_active.is_(True),
        or_(models.User.academic_status.is_(None), func.upper(models.User.academic_status) == "ACTIVE"),
    )
    if academic_program:
        query = query.filter(func.lower(func.trim(models.User.academic_program)) == academic_program.strip().lower())
    if present_year is not None:
        query = query.filter(models.User.present_year == present_year)
    if student_ids:
        query = query.filter(models.User.id.in_(student_ids))
    return query.order_by(models.User.name.asc(), models.User.id.asc()).limit(500).all()


def faculty_can_view(db: Session, faculty_id: int, course_id: int) -> bool:
    coordinator = db.query(models.FacultyCourseAssignment.id).filter_by(faculty_id=faculty_id, course_id=course_id).first()
    expert = db.query(models.SubjectExpertAssignment.id).join(models.Subject).filter(
        models.SubjectExpertAssignment.faculty_id == faculty_id,
        models.Subject.course_id == course_id,
    ).first()
    return bool(coordinator or expert)


def row_payload(enrollment):
    student = enrollment.student
    return {
        "id": enrollment.id, "student_id": student.id, "roll_number": student.roll_number,
        "student_name": student.name, "academic_program": student.academic_program,
        "present_year": student.present_year, "college": student.college,
        "status": enrollment.status, "source": enrollment.enrollment_source,
        "enrolled_at": enrollment.enrolled_at, "updated_at": enrollment.updated_at,
    }
