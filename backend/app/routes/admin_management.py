"""Paginated administrator master workspaces and operations summary (P0-021)."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import and_, asc, desc, func, or_
from sqlalchemy.orm import Session

from app import database, models, schemas
from app.routes.auth import require_roles, require_super_admin
from app.services import admin_management as management
from app.services import authentication as auth_service


router = APIRouter(prefix="/admin", tags=["Admin Management"])
_admin = require_roles("admin")

PAGE_SIZES = (25, 50, 100)
COMMON_QUERY_FIELDS = {
    "search",
    "status",
    "registration_status",
    "college",
    "sort",
    "order",
    "page",
    "page_size",
}
STUDENT_QUERY_FIELDS = COMMON_QUERY_FIELDS | {
    "programme_id",
    "admission_year",
    "present_year",
    "academic_status",
}
FACULTY_QUERY_FIELDS = COMMON_QUERY_FIELDS | {
    "department",
    "designation",
    "employment_status",
    "responsibility",
}
REGISTRATION_STATUSES = {"PENDING_ACTIVATION", "ACTIVE", "DISABLED"}
TAB_STATUSES = {"all", "pending_registration", "active", "inactive", "needs_attention"}
STUDENT_SORTS = {
    "name": (models.User.name, True),
    "roll_number": (models.User.roll_number, True),
    "email": (func.coalesce(models.User.email, models.User.institutional_email), True),
    "mobile": (func.coalesce(models.User.mobile_number, models.User.institutional_mobile), True),
    "college": (models.User.college, True),
    "admission_year": (models.User.admission_year, False),
    "present_year": (models.User.present_year, False),
    "registration_status": (models.User.account_status, True),
    "academic_status": (models.User.academic_status, True),
    "created_at": (models.User.created_at, False),
}
FACULTY_SORTS = {
    "name": (models.User.name, True),
    "employee_code": (models.User.employee_code, True),
    "email": (func.coalesce(models.User.email, models.User.institutional_email), True),
    "mobile": (func.coalesce(models.User.mobile_number, models.User.institutional_mobile), True),
    "college": (models.User.college, True),
    "department": (models.User.department, True),
    "designation": (models.User.designation, True),
    "registration_status": (models.User.account_status, True),
    "employment_status": (models.User.employment_status, True),
    "created_at": (models.User.created_at, False),
}


def _reject_unknown_query_fields(request: Request, allowed: set[str]) -> None:
    unknown = sorted(set(request.query_params.keys()) - allowed)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unsupported filter field: {unknown[0]}")


def _validate_common(
    *,
    status_value: str,
    registration_status: str | None,
    sort: str,
    order: str,
    page_size: int,
    sort_fields: dict,
) -> None:
    if status_value not in TAB_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status tab")
    if registration_status and registration_status not in REGISTRATION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid registration_status")
    if sort not in sort_fields:
        raise HTTPException(status_code=422, detail="Invalid sort field")
    if order not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Invalid sort order")
    if page_size not in PAGE_SIZES:
        raise HTTPException(status_code=422, detail="page_size must be 25, 50 or 100")


def _apply_common_filters(
    query,
    *,
    role: str,
    search: str | None,
    status_value: str,
    registration_status: str | None,
    college: str | None,
):
    query = query.filter(models.User.role == role)
    if search and search.strip():
        term = search.strip()
        identifier = models.User.roll_number if role == "student" else models.User.employee_code
        query = query.filter(
            or_(
                management.escaped_contains(identifier, term),
                management.escaped_contains(models.User.name, term),
                management.escaped_contains(models.User.email, term),
                management.escaped_contains(models.User.institutional_email, term),
                management.escaped_contains(models.User.mobile_number, term),
                management.escaped_contains(models.User.institutional_mobile, term),
            )
        )
    if registration_status:
        query = query.filter(models.User.account_status == registration_status)
    if college and college.strip():
        query = query.filter(management.escaped_contains(models.User.college, college.strip()))

    if status_value == "pending_registration":
        query = query.filter(models.User.account_status == auth_service.ACCOUNT_PENDING)
    elif status_value == "active":
        query = query.filter(
            models.User.is_active.is_(True),
            models.User.account_status == auth_service.ACCOUNT_ACTIVE,
        )
    elif status_value == "inactive":
        query = query.filter(
            or_(
                models.User.is_active.is_(False),
                models.User.account_status == auth_service.ACCOUNT_DISABLED,
            )
        )
    elif status_value == "needs_attention":
        query = query.filter(management.incomplete_master_predicate(role))
    return query


def _apply_order(query, sort_fields: dict, sort: str, order: str):
    expression, is_text = sort_fields[sort]
    sortable = func.lower(expression) if is_text else expression
    direction = asc if order == "asc" else desc
    return query.order_by(expression.is_(None), direction(sortable), asc(models.User.id))


def _student_query(
    db: Session,
    *,
    search: str | None,
    status_value: str,
    registration_status: str | None,
    college: str | None,
    programme_id: int | None,
    admission_year: int | None,
    present_year: int | None,
    academic_status: str | None,
):
    query = _apply_common_filters(
        db.query(models.User),
        role="student",
        search=search,
        status_value=status_value,
        registration_status=registration_status,
        college=college,
    )
    if programme_id is not None:
        query = query.filter(
            models.User.enrollments.any(
                models.StudentCourseEnrollment.course_id == programme_id
            )
        )
    if admission_year is not None:
        query = query.filter(models.User.admission_year == admission_year)
    if present_year is not None:
        query = query.filter(models.User.present_year == present_year)
    if academic_status:
        if academic_status not in {"ACTIVE", "INACTIVE"}:
            raise HTTPException(status_code=422, detail="Invalid academic_status")
        query = query.filter(models.User.academic_status == academic_status)
    return query


def _faculty_query(
    db: Session,
    *,
    search: str | None,
    status_value: str,
    registration_status: str | None,
    college: str | None,
    department: str | None,
    designation: str | None,
    employment_status: str | None,
    responsibility: str | None,
):
    query = _apply_common_filters(
        db.query(models.User),
        role="faculty",
        search=search,
        status_value=status_value,
        registration_status=registration_status,
        college=college,
    )
    if department and department.strip():
        query = query.filter(management.escaped_contains(models.User.department, department.strip()))
    if designation and designation.strip():
        query = query.filter(management.escaped_contains(models.User.designation, designation.strip()))
    if employment_status:
        if employment_status not in {"ACTIVE", "INACTIVE"}:
            raise HTTPException(status_code=422, detail="Invalid employment_status")
        query = query.filter(models.User.employment_status == employment_status)
    if responsibility:
        if responsibility == "course_coordinator":
            query = query.filter(models.User.faculty_courses.any())
        elif responsibility == "subject_expert":
            query = query.filter(models.User.subject_expert_assignments.any())
        elif responsibility == "unassigned":
            query = query.filter(
                ~models.User.faculty_courses.any(),
                ~models.User.subject_expert_assignments.any(),
            )
        else:
            raise HTTPException(status_code=422, detail="Invalid responsibility filter")
    return query


@router.get("/master/students", response_model=schemas.AdminMasterPageOut)
def list_student_master(
    request: Request,
    search: str | None = Query(None, max_length=160),
    status_value: str = Query("all", alias="status"),
    registration_status: str | None = Query(None),
    college: str | None = Query(None, max_length=160),
    programme_id: int | None = Query(None, ge=1),
    admission_year: int | None = Query(None, ge=1900, le=2200),
    present_year: int | None = Query(None, ge=1, le=20),
    academic_status: str | None = Query(None),
    sort: str = Query("name"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    _reject_unknown_query_fields(request, STUDENT_QUERY_FIELDS)
    _validate_common(
        status_value=status_value,
        registration_status=registration_status,
        sort=sort,
        order=order,
        page_size=page_size,
        sort_fields=STUDENT_SORTS,
    )
    query = _student_query(
        db,
        search=search,
        status_value=status_value,
        registration_status=registration_status,
        college=college,
        programme_id=programme_id,
        admission_year=admission_year,
        present_year=present_year,
        academic_status=academic_status,
    )
    total = query.count()
    rows = _apply_order(query, STUDENT_SORTS, sort, order).offset((page - 1) * page_size).limit(page_size).all()
    return schemas.AdminMasterPageOut(
        items=[management.master_record(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/master/faculty", response_model=schemas.AdminMasterPageOut)
def list_faculty_master(
    request: Request,
    search: str | None = Query(None, max_length=160),
    status_value: str = Query("all", alias="status"),
    registration_status: str | None = Query(None),
    college: str | None = Query(None, max_length=160),
    department: str | None = Query(None, max_length=160),
    designation: str | None = Query(None, max_length=120),
    employment_status: str | None = Query(None),
    responsibility: str | None = Query(None),
    sort: str = Query("name"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    _reject_unknown_query_fields(request, FACULTY_QUERY_FIELDS)
    _validate_common(
        status_value=status_value,
        registration_status=registration_status,
        sort=sort,
        order=order,
        page_size=page_size,
        sort_fields=FACULTY_SORTS,
    )
    query = _faculty_query(
        db,
        search=search,
        status_value=status_value,
        registration_status=registration_status,
        college=college,
        department=department,
        designation=designation,
        employment_status=employment_status,
        responsibility=responsibility,
    )
    total = query.count()
    rows = _apply_order(query, FACULTY_SORTS, sort, order).offset((page - 1) * page_size).limit(page_size).all()
    return schemas.AdminMasterPageOut(
        items=[management.master_record(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def _bulk_status(
    db: Session,
    actor: models.User,
    *,
    role: str,
    payload: schemas.AdminBulkStatusRequest,
) -> schemas.AdminBulkResultOut:
    results: list[schemas.AdminBulkResultItem] = []
    for user_id in dict.fromkeys(payload.ids):
        user = db.query(models.User).filter(models.User.id == user_id, models.User.role == role).first()
        if not user:
            results.append(schemas.AdminBulkResultItem(id=user_id, success=False, error=f"{role.capitalize()} not found"))
            continue
        activate = payload.action == "activate"
        if not activate and user.is_active:
            user.session_version = (user.session_version or 1) + 1
        user.is_active = activate
        if role == "student":
            user.academic_status = "ACTIVE" if activate else "INACTIVE"
        else:
            user.employment_status = "ACTIVE" if activate else "INACTIVE"
        management.record_audit(
            db,
            actor,
            action=f"{role}.{payload.action}",
            target_type=role,
            target_id=user.id,
            summary=f"{role.capitalize()} record {payload.action}d",
            changed_fields=["is_active", "academic_status" if role == "student" else "employment_status"],
        )
        results.append(schemas.AdminBulkResultItem(id=user_id, success=True))
    db.commit()
    succeeded = sum(1 for item in results if item.success)
    return schemas.AdminBulkResultOut(succeeded=succeeded, failed=len(results) - succeeded, results=results)


@router.post("/master/students/bulk-status", response_model=schemas.AdminBulkResultOut)
def bulk_student_status(
    payload: schemas.AdminBulkStatusRequest,
    db: Session = Depends(database.get_db),
    actor: models.User = Depends(_admin),
):
    return _bulk_status(db, actor, role="student", payload=payload)


@router.post("/master/faculty/bulk-status", response_model=schemas.AdminBulkResultOut)
def bulk_faculty_status(
    payload: schemas.AdminBulkStatusRequest,
    db: Session = Depends(database.get_db),
    actor: models.User = Depends(_admin),
):
    return _bulk_status(db, actor, role="faculty", payload=payload)


@router.post("/master/faculty/bulk-assignment", response_model=schemas.AdminBulkResultOut)
def bulk_faculty_assignment(
    payload: schemas.AdminBulkAssignmentRequest,
    db: Session = Depends(database.get_db),
    actor: models.User = Depends(_admin),
):
    if payload.assignment_type == "course_coordinator":
        target = db.query(models.Course).filter(models.Course.id == payload.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Course not found")
        assignment_model = models.FacultyCourseAssignment
        target_column = assignment_model.course_id
        target_label = "course"
    else:
        target = db.query(models.Subject).filter(models.Subject.id == payload.target_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="Subject not found")
        assignment_model = models.SubjectExpertAssignment
        target_column = assignment_model.subject_id
        target_label = "subject"

    results: list[schemas.AdminBulkResultItem] = []
    for faculty_id in dict.fromkeys(payload.faculty_ids):
        faculty = db.query(models.User).filter(models.User.id == faculty_id, models.User.role == "faculty").first()
        if not faculty:
            results.append(schemas.AdminBulkResultItem(id=faculty_id, success=False, error="Faculty not found"))
            continue
        if not faculty.is_active:
            results.append(schemas.AdminBulkResultItem(id=faculty_id, success=False, error="Faculty account is inactive"))
            continue
        existing = db.query(assignment_model).filter(
            assignment_model.faculty_id == faculty_id,
            target_column == payload.target_id,
        ).first()
        if existing:
            results.append(schemas.AdminBulkResultItem(id=faculty_id, success=False, error="Assignment already exists"))
            continue
        assignment = assignment_model(faculty_id=faculty_id)
        setattr(assignment, f"{target_label}_id", payload.target_id)
        db.add(assignment)
        management.record_audit(
            db,
            actor,
            action=f"faculty.assign_{payload.assignment_type}",
            target_type="faculty",
            target_id=faculty_id,
            summary=f"Faculty assigned as {payload.assignment_type.replace('_', ' ')}",
            changed_fields=[f"{target_label}_id"],
        )
        results.append(schemas.AdminBulkResultItem(id=faculty_id, success=True))
    db.commit()
    succeeded = sum(1 for item in results if item.success)
    return schemas.AdminBulkResultOut(succeeded=succeeded, failed=len(results) - succeeded, results=results)


def _csv_safe(value) -> str:
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@")):
        return f"'{text}"
    return text


def _csv_response(role: str, records: list[schemas.AdminMasterRecordOut]) -> Response:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    if role == "student":
        headers = ["Roll Number", "Name", "Email", "Mobile", "College", "Programme", "Admission Year", "Present Year", "Registration Status", "Academic Status"]
    else:
        headers = ["Employee Code", "Name", "Email", "Mobile", "College", "Department", "Designation", "Registration Status", "Employment Status", "Coordinator Assignments", "Subject Expert Assignments"]
    writer.writerow(headers)
    for record in records:
        if role == "student":
            row = [
                record.roll_number,
                record.name,
                record.email,
                record.mobile_masked,
                record.college,
                "; ".join(programme.title for programme in record.programmes),
                record.admission_year,
                record.present_year,
                record.registration_status,
                record.academic_status,
            ]
        else:
            row = [
                record.employee_code,
                record.name,
                record.email,
                record.mobile_masked,
                record.college,
                record.department,
                record.designation,
                record.registration_status,
                record.employment_status,
                record.coordinator_assignments,
                record.subject_expert_assignments,
            ]
        writer.writerow([_csv_safe(value) for value in row])
    filename = f"SYS_{role}_master_{datetime.now(timezone.utc).strftime('%Y%m%d')}.csv"
    return Response(
        content=stream.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/master/students/export")
def export_student_master(
    request: Request,
    search: str | None = Query(None, max_length=160),
    status_value: str = Query("all", alias="status"),
    registration_status: str | None = Query(None),
    college: str | None = Query(None, max_length=160),
    programme_id: int | None = Query(None, ge=1),
    admission_year: int | None = Query(None, ge=1900, le=2200),
    present_year: int | None = Query(None, ge=1, le=20),
    academic_status: str | None = Query(None),
    sort: str = Query("name"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    _reject_unknown_query_fields(request, STUDENT_QUERY_FIELDS)
    _validate_common(status_value=status_value, registration_status=registration_status, sort=sort, order=order, page_size=page_size, sort_fields=STUDENT_SORTS)
    query = _student_query(db, search=search, status_value=status_value, registration_status=registration_status, college=college, programme_id=programme_id, admission_year=admission_year, present_year=present_year, academic_status=academic_status)
    rows = _apply_order(query, STUDENT_SORTS, sort, order).all()
    return _csv_response("student", [management.master_record(db, row) for row in rows])


@router.get("/master/faculty/export")
def export_faculty_master(
    request: Request,
    search: str | None = Query(None, max_length=160),
    status_value: str = Query("all", alias="status"),
    registration_status: str | None = Query(None),
    college: str | None = Query(None, max_length=160),
    department: str | None = Query(None, max_length=160),
    designation: str | None = Query(None, max_length=120),
    employment_status: str | None = Query(None),
    responsibility: str | None = Query(None),
    sort: str = Query("name"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    _reject_unknown_query_fields(request, FACULTY_QUERY_FIELDS)
    _validate_common(status_value=status_value, registration_status=registration_status, sort=sort, order=order, page_size=page_size, sort_fields=FACULTY_SORTS)
    query = _faculty_query(db, search=search, status_value=status_value, registration_status=registration_status, college=college, department=department, designation=designation, employment_status=employment_status, responsibility=responsibility)
    rows = _apply_order(query, FACULTY_SORTS, sort, order).all()
    return _csv_response("faculty", [management.master_record(db, row) for row in rows])


def _readiness_item(key: str, label: str, complete: bool | None, detail: str) -> dict:
    status_value = "unavailable" if complete is None else "complete" if complete else "needs_attention"
    return {"key": key, "label": label, "status": status_value, "detail": detail}


@router.get("/operations/summary")
def operations_summary(
    db: Session = Depends(database.get_db),
    actor: models.User = Depends(_admin),
):
    students = db.query(models.User).filter(models.User.role == "student")
    faculty = db.query(models.User).filter(models.User.role == "faculty")
    student_total = students.count()
    faculty_total = faculty.count()
    student_active = students.filter(models.User.is_active.is_(True), models.User.account_status == auth_service.ACCOUNT_ACTIVE).count()
    faculty_active = faculty.filter(models.User.is_active.is_(True), models.User.account_status == auth_service.ACCOUNT_ACTIVE).count()
    student_pending = students.filter(models.User.account_status == auth_service.ACCOUNT_PENDING).count()
    faculty_pending = faculty.filter(models.User.account_status == auth_service.ACCOUNT_PENDING).count()

    active_courses = db.query(models.Course).filter(models.Course.is_active.is_(True)).count()
    draft_courses = db.query(models.Course).filter(models.Course.is_active.is_(False)).count()
    subjects_total = db.query(models.Subject).count()
    topics_total = db.query(models.Topic).count()
    questions_total = db.query(models.Question).count()
    assessments_total = db.query(models.Assessment).count()
    sessions_total = db.query(models.LearningSession).count()
    recipient_total = db.query(models.NotificationRecipient).filter(models.NotificationRecipient.is_active.is_(True)).count()

    courses_without_coordinators = (
        db.query(models.Course)
        .filter(models.Course.is_active.is_(True), ~models.Course.faculty_assignments.any())
        .count()
    )
    subjects_without_experts = db.query(models.Subject).filter(~models.Subject.expert_assignments.any()).count()
    incomplete_students = students.filter(management.incomplete_master_predicate("student")).count()
    incomplete_faculty = faculty.filter(management.incomplete_master_predicate("faculty")).count()
    failed_notifications = db.query(models.NotificationDelivery).filter(
        or_(
            models.NotificationDelivery.failure_reason.is_not(None),
            func.upper(models.NotificationDelivery.status).in_(("FAILED", "ERROR", "DEAD_LETTER")),
        )
    ).count()
    students_requiring_attention = (
        db.query(func.count(func.distinct(models.LearningGap.student_id)))
        .filter(models.LearningGap.is_high_priority.is_(True))
        .scalar()
        or 0
    )
    attention_total = (
        student_pending
        + faculty_pending
        + incomplete_students
        + incomplete_faculty
        + courses_without_coordinators
        + subjects_without_experts
        + failed_notifications
        + students_requiring_attention
    )

    subject_ids_with_topics = {
        row[0] for row in db.query(models.Topic.subject_id).filter(models.Topic.subject_id.is_not(None)).distinct().all()
    }
    subjects_without_topics = db.query(models.Subject).filter(~models.Subject.id.in_(subject_ids_with_topics)).count() if subjects_total else 0
    contacts_available = (
        db.query(models.User)
        .filter(
            models.User.role.in_(("student", "faculty")),
            or_(
                models.User.email.is_not(None),
                models.User.institutional_email.is_not(None),
                models.User.mobile_number.is_not(None),
                models.User.institutional_mobile.is_not(None),
            ),
        )
        .count()
    )
    master_total = student_total + faculty_total
    readiness = [
        _readiness_item("institution", "Institution profile configured", None, "No institution-profile provider exists."),
        _readiness_item("masters", "Student/faculty masters available", master_total > 0, f"{student_total} students and {faculty_total} faculty records."),
        _readiness_item("contacts", "Registration contacts available", master_total > 0 and contacts_available == master_total, f"{contacts_available} of {master_total} master records have a registration contact."),
        _readiness_item("programmes", "Programmes created", active_courses + draft_courses > 0, f"{active_courses + draft_courses} programmes are configured."),
        _readiness_item("subjects", "Subjects configured", subjects_total > 0, f"{subjects_total} subjects are configured."),
        _readiness_item("responsibilities", "Coordinators and experts assigned", active_courses > 0 and subjects_total > 0 and courses_without_coordinators == 0 and subjects_without_experts == 0, f"{courses_without_coordinators} programmes lack coordinators; {subjects_without_experts} subjects lack experts."),
        _readiness_item("syllabus", "Syllabus structure configured", subjects_total > 0 and subjects_without_topics == 0, f"{subjects_without_topics} subjects have no topics."),
        _readiness_item("questions", "Question intelligence available", questions_total > 0, f"{questions_total} questions are available."),
        _readiness_item("operations", "Learning/assessment operations ready", assessments_total > 0 and sessions_total > 0, f"{assessments_total} assessments and {sessions_total} learning sessions exist."),
        _readiness_item("notifications", "Notification delivery configured", recipient_total > 0, f"{recipient_total} active notification recipients are configured."),
    ]

    recent_assessments = db.query(models.Assessment).order_by(models.Assessment.created_at.desc(), models.Assessment.id.desc()).limit(4).all()
    recent_sessions = db.query(models.LearningSession).order_by(models.LearningSession.created_at.desc(), models.LearningSession.id.desc()).limit(4).all()
    unread_notifications = db.query(models.NotificationDelivery).filter(
        models.NotificationDelivery.user_id == actor.id,
        models.NotificationDelivery.is_read.is_(False),
    ).count()

    recent_activity = {"available": False, "items": [], "reason": "Audit activity is restricted to Super Admin."}
    if (actor.role or "").lower() == "super_admin":
        audit_rows = db.query(models.AdminAuditLog).order_by(models.AdminAuditLog.created_at.desc(), models.AdminAuditLog.id.desc()).limit(6).all()
        recent_activity = {
            "available": True,
            "items": [
                {
                    "id": row.id,
                    "summary": row.summary,
                    "action": row.action,
                    "created_at": row.created_at,
                }
                for row in audit_rows
            ],
            "reason": None,
        }

    return {
        "generated_at": datetime.now(timezone.utc),
        "scope_label": "Platform-wide" if actor.role == "super_admin" else actor.college,
        "unread_notifications": unread_notifications,
        "students": {"total": student_total, "active": student_active, "pending_activation": student_pending},
        "faculty": {"total": faculty_total, "active": faculty_active, "pending_activation": faculty_pending},
        "programmes": {"total": active_courses + draft_courses, "active": active_courses, "draft": draft_courses},
        "attention_required": {"total": attention_total},
        "attention": [
            {"key": "pending_activations", "label": "Pending account activations", "count": student_pending + faculty_pending, "href": "/admin/students?status=pending_registration"},
            {"key": "incomplete_masters", "label": "Inactive or incomplete master records", "count": incomplete_students + incomplete_faculty, "href": "/admin/students?status=needs_attention"},
            {"key": "programme_coordinators", "label": "Programmes without coordinators", "count": courses_without_coordinators, "href": "/admin/faculty?responsibility=unassigned"},
            {"key": "subject_experts", "label": "Subjects without experts", "count": subjects_without_experts, "href": "/admin/faculty?responsibility=unassigned"},
            {"key": "notification_failures", "label": "Failed notification deliveries", "count": failed_notifications, "href": "/admin/notifications"},
            {"key": "student_attention", "label": "Students requiring attention", "count": students_requiring_attention, "href": "/analytics/admin"},
        ],
        "readiness": readiness,
        "academic_operations": {
            "programmes": active_courses + draft_courses,
            "subjects": subjects_total,
            "coordinator_assignments": db.query(models.FacultyCourseAssignment).count(),
            "expert_assignments": db.query(models.SubjectExpertAssignment).count(),
        },
        "recent_operations": {
            "assessments": [{"id": row.id, "title": row.title, "status": row.status, "created_at": row.created_at} for row in recent_assessments],
            "learning_sessions": [{"id": row.id, "title": row.title, "status": row.status, "created_at": row.created_at} for row in recent_sessions],
        },
        "early_warning": {"students_requiring_attention": students_requiring_attention},
        "recent_admin_activity": recent_activity,
    }


@router.get("/audit-logs", response_model=list[schemas.AdminAuditLogOut])
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(database.get_db),
    _: models.User = Depends(require_super_admin),
):
    rows = db.query(models.AdminAuditLog).order_by(models.AdminAuditLog.created_at.desc(), models.AdminAuditLog.id.desc()).limit(limit).all()
    return [
        schemas.AdminAuditLogOut(
            id=row.id,
            actor_user_id=row.actor_user_id,
            actor_name=row.actor.name if row.actor else None,
            action=row.action,
            target_type=row.target_type,
            target_id=row.target_id,
            summary=row.summary,
            created_at=row.created_at,
        )
        for row in rows
    ]
