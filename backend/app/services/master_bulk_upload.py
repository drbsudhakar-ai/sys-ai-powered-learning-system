"""Validated, auditable imports for institutional student and faculty masters."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.services import admin_management, authentication


MAX_BATCH_SIZE = 500


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _normalize_mobile(value: object) -> str:
    mobile = re.sub(r"[\s().-]", "", _text(value))
    if re.fullmatch(r"[6-9]\d{9}", mobile):
        mobile = f"+91{mobile}"
    elif re.fullmatch(r"91[6-9]\d{9}", mobile):
        mobile = f"+{mobile}"
    return authentication.normalize_mobile(mobile)


def _year(value: object, label: str, minimum: int, maximum: int) -> int:
    try:
        number = int(_text(value))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a whole number") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")
    return number


def import_master_records(
    db: Session,
    current_admin: models.User,
    records: list[dict],
    *,
    role: str,
) -> dict:
    if not records:
        raise HTTPException(status_code=422, detail="Select at least one record to upload")
    if len(records) > MAX_BATCH_SIZE:
        raise HTTPException(status_code=422, detail=f"Upload at most {MAX_BATCH_SIZE} records at a time")

    identifier_key = "roll_number" if role == "student" else "employee_code"
    identifier_column = models.User.roll_number if role == "student" else models.User.employee_code
    skipped: list[str] = []
    invalid: list[dict] = []
    prepared: list[models.User] = []
    seen_identifiers: set[str] = set()
    seen_emails: set[str] = set()
    seen_mobiles: set[str] = set()

    for index, record in enumerate(records, start=2):
        identifier = _text(record.get(identifier_key)).upper()
        try:
            if not identifier or len(identifier) > 50:
                raise ValueError(f"A valid {identifier_key.replace('_', ' ')} is required")
            if identifier in seen_identifiers:
                skipped.append(identifier)
                continue
            seen_identifiers.add(identifier)

            existing = db.query(models.User.id).filter(
                func.upper(func.trim(identifier_column)) == identifier
            ).first()
            if existing:
                skipped.append(identifier)
                continue

            name = _text(record.get("name"))
            if not name or len(name) > 100:
                raise ValueError("A valid name is required")
            email = authentication.normalize_email(_text(record.get("email")))
            mobile = _normalize_mobile(record.get("mobile_number"))
            if email in seen_emails:
                raise ValueError("Email is duplicated in this upload")
            if mobile in seen_mobiles:
                raise ValueError("Mobile number is duplicated in this upload")
            admin_management.ensure_unique_email(db, email)
            admin_management.ensure_unique_mobile(db, mobile)

            college = _text(record.get("college"))
            department = _text(record.get("department"))
            if not college or not department:
                raise ValueError("College and department are required")

            fields = {
                "name": name,
                "role": role,
                "email": None,
                "mobile_number": None,
                "institutional_email": email,
                "institutional_mobile": mobile,
                "hashed_password": None,
                "is_active": True,
                "account_status": authentication.ACCOUNT_PENDING,
                "email_verified": False,
                "mobile_verified": False,
                "mobile_is_personal": True,
                "college": college,
                "department": department,
                identifier_key: identifier,
            }

            if role == "faculty":
                designation = _text(record.get("designation"))
                employment_status = _text(record.get("employment_status")).upper()
                if not designation:
                    raise ValueError("Designation is required")
                if employment_status not in {"ACTIVE", "INACTIVE"}:
                    raise ValueError("Employment status must be ACTIVE or INACTIVE")
                fields.update(designation=designation, employment_status=employment_status)
            else:
                academic_program = _text(record.get("academic_program"))
                academic_status = _text(record.get("academic_status")).upper()
                if not academic_program:
                    raise ValueError("Academic programme is required")
                if academic_status not in {"ACTIVE", "INACTIVE"}:
                    raise ValueError("Academic status must be ACTIVE or INACTIVE")
                fields.update(
                    academic_program=academic_program,
                    admission_year=_year(record.get("admission_year"), "Admission year", 1900, 2200),
                    present_year=_year(record.get("present_year"), "Present year", 1, 20),
                    academic_status=academic_status,
                )

            prepared.append(models.User(**fields))
            seen_emails.add(email)
            seen_mobiles.add(mobile)
        except (TypeError, ValueError) as exc:
            invalid.append({"row": index, identifier_key: identifier or None, "reason": str(exc)})

    if prepared:
        try:
            db.add_all(prepared)
            admin_management.record_audit(
                db,
                current_admin,
                action=f"master.{role}.bulk_upload",
                target_type=f"{role}_master",
                target_id=None,
                summary=f"Imported {len(prepared)} {role} master records",
                changed_fields=[identifier_key, "institutional_email", "institutional_mobile"],
            )
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="One or more records conflict with existing master data. Refresh and try again.",
            ) from exc

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "admin_user": current_admin.id,
        "total_uploaded": len(records),
        "inserted": len(prepared),
        "skipped": len(skipped),
        "invalid": len(invalid),
    }
    return {
        "status": "success" if prepared else "skipped",
        "inserted": len(prepared),
        "skipped": len(skipped),
        "invalid": len(invalid),
        f"skipped_{'roll_numbers' if role == 'student' else 'employee_codes'}": skipped,
        "invalid_records": invalid,
        "log_entry": log_entry,
    }
