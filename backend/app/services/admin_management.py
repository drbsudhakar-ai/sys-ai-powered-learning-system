"""Shared validation and presentation helpers for administrator master data."""

from __future__ import annotations

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app import models, schemas
from app.services import authentication as auth_service


def clean_optional_text(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def ensure_unique_email(
    db: Session,
    value: str | None,
    *,
    exclude_user_id: int | None = None,
) -> str | None:
    if value is None or not str(value).strip():
        return None
    normalized = auth_service.normalize_email(str(value))
    query = db.query(models.User.id).filter(
        or_(
            func.lower(func.trim(models.User.email)) == normalized,
            func.lower(func.trim(models.User.institutional_email)) == normalized,
        )
    )
    if exclude_user_id is not None:
        query = query.filter(models.User.id != exclude_user_id)
    if query.first():
        raise ValueError("Email already exists")
    return normalized


def ensure_unique_mobile(
    db: Session,
    value: str | None,
    *,
    exclude_user_id: int | None = None,
) -> str | None:
    if value is None or not str(value).strip():
        return None
    normalized = auth_service.normalize_mobile(str(value))
    query = db.query(models.User.id).filter(
        or_(
            func.trim(models.User.mobile_number) == normalized,
            func.trim(models.User.institutional_mobile) == normalized,
        )
    )
    if exclude_user_id is not None:
        query = query.filter(models.User.id != exclude_user_id)
    if query.first():
        raise ValueError("Mobile number already exists")
    return normalized


def record_audit(
    db: Session,
    actor: models.User,
    *,
    action: str,
    target_type: str,
    target_id: int | None,
    summary: str,
    changed_fields: list[str] | None = None,
) -> models.AdminAuditLog:
    row = models.AdminAuditLog(
        actor_user_id=actor.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        summary=summary[:255],
        details={"changed_fields": sorted(set(changed_fields or []))},
    )
    db.add(row)
    return row


def mask_mobile(value: str | None) -> str | None:
    if not value:
        return None
    digits = str(value).strip()
    if len(digits) <= 4:
        return "••••"
    return f"••••••{digits[-4:]}"


def master_record(db: Session, user: models.User) -> schemas.AdminMasterRecordOut:
    programmes: list[schemas.MasterProgrammeOut] = []
    coordinator_count = 0
    expert_count = 0
    if user.role == "student":
        rows = (
            db.query(models.Course.id, models.Course.title)
            .join(
                models.StudentCourseEnrollment,
                models.StudentCourseEnrollment.course_id == models.Course.id,
            )
            .filter(models.StudentCourseEnrollment.student_id == user.id)
            .order_by(models.Course.title, models.Course.id)
            .all()
        )
        programmes = [schemas.MasterProgrammeOut(id=row[0], title=row[1]) for row in rows]
    elif user.role == "faculty":
        coordinator_count = (
            db.query(models.FacultyCourseAssignment.id)
            .filter(models.FacultyCourseAssignment.faculty_id == user.id)
            .count()
        )
        expert_count = (
            db.query(models.SubjectExpertAssignment.id)
            .filter(models.SubjectExpertAssignment.faculty_id == user.id)
            .count()
        )

    email = user.email or user.institutional_email
    mobile = user.mobile_number or user.institutional_mobile
    return schemas.AdminMasterRecordOut(
        id=user.id,
        role=user.role,
        name=user.name,
        roll_number=user.roll_number,
        employee_code=user.employee_code,
        email=email,
        email_verified=bool(user.email_verified),
        mobile_masked=mask_mobile(mobile),
        mobile_verified=bool(user.mobile_verified and user.mobile_is_personal),
        registration_status=user.account_status,
        is_active=bool(user.is_active),
        college=user.college,
        department=user.department,
        designation=user.designation,
        admission_year=user.admission_year,
        present_year=user.present_year,
        academic_status=user.academic_status,
        employment_status=user.employment_status,
        programmes=programmes,
        coordinator_assignments=coordinator_count,
        subject_expert_assignments=expert_count,
        last_login_at=None,
        last_login_available=False,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def escaped_contains(column, value: str):
    escaped = value.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.lower(func.coalesce(column, "")).like(f"%{escaped}%", escape="\\")


def incomplete_master_predicate(role: str):
    contact_missing = and_(
        models.User.email.is_(None),
        models.User.institutional_email.is_(None),
        models.User.mobile_number.is_(None),
        models.User.institutional_mobile.is_(None),
    )
    identifier_missing = (
        or_(models.User.roll_number.is_(None), func.trim(models.User.roll_number) == "")
        if role == "student"
        else or_(models.User.employee_code.is_(None), func.trim(models.User.employee_code) == "")
    )
    return or_(contact_missing, identifier_missing, func.trim(models.User.name) == "")
