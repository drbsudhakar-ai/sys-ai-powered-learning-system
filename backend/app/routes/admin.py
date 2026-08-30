"""
Admin Student / Faculty / Academic Responsibility routes (P0-008)
"""

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import List
from math import isclose
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import uuid

from app import models, schemas, database, utils
from app.routes.auth import require_roles
from app.services import authentication as auth_service
from app.services import admin_management as management_service
from app.services.course_profile_pdf import build_coordinator_courses_pdf, build_course_profile_pdf, build_subject_expert_assignments_pdf

router = APIRouter(prefix="/admin", tags=["Admin"])
_admin = require_roles("admin")
_academic_staff = require_roles("admin", "faculty")
_faculty = require_roles("faculty")

PROFILE_PHOTO_MAX_BYTES = 5 * 1024 * 1024
PROFILE_PHOTO_TYPES = {
    "image/jpeg": (".jpg", (b"\xff\xd8\xff",)),
    "image/png": (".png", (b"\x89PNG\r\n\x1a\n",)),
    "image/webp": (".webp", (b"RIFF",)),
}
PROFILE_PHOTO_DIRECTORY = Path(__file__).resolve().parents[3] / "frontend" / "public" / "photos"


def _registration_complete(user: models.User) -> bool:
    """A usable credential, not a legacy status value, proves registration."""
    return utils.is_usable_password_hash(user.hashed_password) and user.account_status == auth_service.ACCOUNT_ACTIVE


def _existing_profile_photo_url(user: models.User) -> str | None:
    if user.photo_url:
        return user.photo_url
    identifier = user.roll_number if user.role == "student" else user.employee_code
    if not identifier or not PROFILE_PHOTO_DIRECTORY.is_dir():
        return None
    expected_stems = {f"{user.role}-{identifier}".lower(), str(identifier).lower()}
    for path in PROFILE_PHOTO_DIRECTORY.iterdir():
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            if path.stem.lower() in expected_stems:
                return f"/photos/{path.name}"
    return None


def _user_out(user: models.User) -> schemas.UserOut:
    return schemas.UserOut.model_validate(user).model_copy(
        update={
            "photo_url": _existing_profile_photo_url(user),
            "registration_complete": _registration_complete(user),
        }
    )


def _coordinator_out(row: models.FacultyCourseAssignment) -> schemas.CourseCoordinatorOut:
    return schemas.CourseCoordinatorOut(
        id=row.id,
        faculty_id=row.faculty_id,
        faculty_name=row.faculty.name if row.faculty else "",
        faculty_email=(row.faculty.email or row.faculty.institutional_email) if row.faculty else None,
        course_id=row.course_id,
        course_title=row.course.title if row.course else "",
        assigned_at=row.assigned_at,
    )


def _expert_out(row: models.SubjectExpertAssignment) -> schemas.SubjectExpertOut:
    return schemas.SubjectExpertOut(
        id=row.id,
        faculty_id=row.faculty_id,
        faculty_name=row.faculty.name if row.faculty else "",
        faculty_email=(row.faculty.email or row.faculty.institutional_email) if row.faculty else None,
        subject_id=row.subject_id,
        subject_name=row.subject.name if row.subject else "",
        course_id=row.subject.course_id if row.subject else None,
        course_title=row.subject.course.title if row.subject and row.subject.course else None,
        assigned_at=row.assigned_at,
    )


def _get_role_user(db: Session, user_id: int, role: str) -> models.User:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user or (user.role or "").lower() != role:
        raise HTTPException(status_code=404, detail=f"{role.capitalize()} not found")
    return user


def _managed_photo_path(photo_url: str | None) -> Path | None:
    if not photo_url or not photo_url.startswith("/photos/"):
        return None
    filename = Path(photo_url).name
    if not re.fullmatch(r"(?:student|faculty)-\d+-[a-f0-9]{12}\.(?:jpg|png|webp)", filename):
        return None
    path = (PROFILE_PHOTO_DIRECTORY / filename).resolve()
    return path if path.parent == PROFILE_PHOTO_DIRECTORY.resolve() else None


async def _save_profile_photo(upload: UploadFile, *, role: str, user_id: int) -> tuple[str, Path]:
    content_type = (upload.content_type or "").lower()
    definition = PROFILE_PHOTO_TYPES.get(content_type)
    if not definition:
        raise HTTPException(status_code=422, detail="Profile photo must be JPEG, PNG or WebP")
    content = await upload.read(PROFILE_PHOTO_MAX_BYTES + 1)
    await upload.close()
    if not content:
        raise HTTPException(status_code=422, detail="Profile photo is empty")
    if len(content) > PROFILE_PHOTO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Profile photo must not exceed 5 MB")
    extension, signatures = definition
    valid_signature = any(content.startswith(signature) for signature in signatures)
    if content_type == "image/webp":
        valid_signature = valid_signature and len(content) >= 12 and content[8:12] == b"WEBP"
    if not valid_signature:
        raise HTTPException(status_code=422, detail="Profile photo content does not match its file type")
    PROFILE_PHOTO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    filename = f"{role}-{user_id}-{uuid.uuid4().hex[:12]}{extension}"
    path = PROFILE_PHOTO_DIRECTORY / filename
    path.write_bytes(content)
    return f"/photos/{filename}", path


async def _upload_role_photo(
    *, db: Session, actor: models.User, user_id: int, role: str, photo: UploadFile
):
    user = _get_role_user(db, user_id, role)
    previous = _managed_photo_path(user.photo_url)
    photo_url, written_path = await _save_profile_photo(photo, role=role, user_id=user.id)
    try:
        user.photo_url = photo_url
        management_service.record_audit(
            db,
            actor,
            action=f"{role}.photo.update",
            target_type=role,
            target_id=user.id,
            summary=f"Updated {role} profile photo",
            changed_fields=["photo_url"],
        )
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        written_path.unlink(missing_ok=True)
        raise
    if previous and previous != written_path:
        previous.unlink(missing_ok=True)
    return {"photo_url": user.photo_url}


def _remove_role_photo(*, db: Session, actor: models.User, user_id: int, role: str):
    user = _get_role_user(db, user_id, role)
    previous = _managed_photo_path(user.photo_url)
    user.photo_url = None
    management_service.record_audit(
        db,
        actor,
        action=f"{role}.photo.remove",
        target_type=role,
        target_id=user.id,
        summary=f"Removed {role} profile photo",
        changed_fields=["photo_url"],
    )
    db.commit()
    if previous:
        previous.unlink(missing_ok=True)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _normalized_identifier(
    db: Session,
    *,
    column,
    value: str | None,
    required_detail: str,
    duplicate_detail: str,
    exclude_user_id: int | None = None,
) -> str:
    if not (value or "").strip():
        raise HTTPException(status_code=422, detail=required_detail)
    try:
        normalized = auth_service.normalize_institutional_id(value or "")
    except ValueError as exc:
        raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
    query = db.query(models.User).filter(
        auth_service.normalized_identifier_expression(column) == normalized
    )
    if exclude_user_id is not None:
        query = query.filter(models.User.id != exclude_user_id)
    if query.first():
        raise HTTPException(status_code=409, detail=duplicate_detail)
    return normalized


def _commit_identifier_user(
    db: Session,
    user: models.User,
    duplicate_detail: str,
    *,
    actor: models.User | None = None,
    action: str | None = None,
    target_type: str | None = None,
    changed_fields: list[str] | None = None,
) -> schemas.UserOut:
    try:
        db.add(user)
        db.flush()
        if actor and action and target_type:
            management_service.record_audit(
                db,
                actor,
                action=action,
                target_type=target_type,
                target_id=user.id,
                summary=f"{target_type.capitalize()} master record {action.split('.')[-1]}",
                changed_fields=changed_fields,
            )
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=duplicate_detail)
    return _user_out(user)


@router.post("/users/provision", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def provision_user(
    payload: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    """Explicit administrator-only immediate account provisioning."""

    return auth_service.provision_active_user(
        db,
        name=payload.name,
        email=str(payload.email),
        role=payload.role,
        password=payload.password.get_secret_value(),
        roll_number=payload.roll_number,
        employee_code=payload.employee_code,
        mobile_number=payload.mobile_number,
    )


@router.post(
    "/users/master-upload",
    response_model=List[schemas.UserOut],
    status_code=status.HTTP_201_CREATED,
)
def master_upload_users(
    payload: schemas.AdminMasterBatchCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    """Validate and create a student/faculty master batch atomically."""

    seen_roll_numbers: set[str] = set()
    seen_employee_codes: set[str] = set()
    seen_emails: set[str] = set()
    seen_mobiles: set[str] = set()
    users: list[models.User] = []

    for record in payload.records:
        if record.role == "student":
            if record.employee_code is not None:
                raise HTTPException(status_code=422, detail="employee_code is not valid for students")
            roll_number = _normalized_identifier(
                db,
                column=models.User.roll_number,
                value=record.roll_number,
                required_detail="roll_number is required for students",
                duplicate_detail="Roll number already exists",
            )
            if roll_number in seen_roll_numbers:
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate roll number in master-upload batch",
                )
            seen_roll_numbers.add(roll_number)
            employee_code = None
            if record.department is not None or record.designation is not None or record.employment_status is not None:
                raise HTTPException(status_code=422, detail="Faculty employment fields are not valid for students")
        else:
            if record.roll_number is not None:
                raise HTTPException(status_code=422, detail="roll_number is not valid for faculty")
            employee_code = _normalized_identifier(
                db,
                column=models.User.employee_code,
                value=record.employee_code,
                required_detail="employee_code is required for faculty",
                duplicate_detail="Employee code already exists",
            )
            if employee_code in seen_employee_codes:
                raise HTTPException(
                    status_code=409,
                    detail="Duplicate employee code in master-upload batch",
                )
            seen_employee_codes.add(employee_code)
            roll_number = None
            if record.academic_program is not None or record.admission_year is not None or record.present_year is not None or record.academic_status is not None:
                raise HTTPException(status_code=422, detail="Student academic fields are not valid for faculty")

        try:
            institutional_email = management_service.ensure_unique_email(
                db, str(record.email) if record.email else None
            )
            institutional_mobile = management_service.ensure_unique_mobile(
                db, record.mobile_number
            )
        except ValueError as exc:
            raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
        if institutional_email:
            if institutional_email in seen_emails:
                raise HTTPException(status_code=409, detail="Duplicate email in master-upload batch")
            seen_emails.add(institutional_email)
        if institutional_mobile:
            if institutional_mobile in seen_mobiles:
                raise HTTPException(status_code=409, detail="Duplicate mobile number in master-upload batch")
            seen_mobiles.add(institutional_mobile)

        users.append(
            models.User(
                name=record.name.strip(),
                email=None,
                institutional_email=institutional_email,
                institutional_mobile=institutional_mobile,
                hashed_password=None,
                role=record.role,
                roll_number=roll_number,
                employee_code=employee_code,
                photo_url=record.photo_url,
                is_active=True,
                account_status=auth_service.ACCOUNT_PENDING,
                email_verified=False,
                mobile_verified=False,
                mobile_is_personal=record.mobile_is_personal,
                college=management_service.clean_optional_text(record.college),
                academic_program=(management_service.clean_optional_text(record.academic_program) if record.role == "student" else None),
                department=(management_service.clean_optional_text(record.department) if record.role == "faculty" else None),
                designation=(management_service.clean_optional_text(record.designation) if record.role == "faculty" else None),
                admission_year=(record.admission_year if record.role == "student" else None),
                present_year=(record.present_year if record.role == "student" else None),
                academic_status=((record.academic_status or "ACTIVE") if record.role == "student" else None),
                employment_status=((record.employment_status or "ACTIVE") if record.role == "faculty" else None),
            )
        )

    try:
        db.add_all(users)
        db.flush()
        management_service.record_audit(
            db,
            current_admin,
            action="master.batch_create",
            target_type="user_master",
            target_id=None,
            summary=f"Created {len(users)} student/faculty master records",
            changed_fields=["records"],
        )
        db.commit()
        for user in users:
            db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate institutional identifier")
    return users


@router.post("/users/{user_id}/disable", response_model=schemas.UserOut)
def disable_user_account(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=409, detail="Administrators cannot disable their own account")
    user.account_status = auth_service.ACCOUNT_DISABLED
    user.session_version = (user.session_version or 1) + 1
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/enable", response_model=schemas.UserOut)
def enable_user_account(
    user_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.account_status = (
        auth_service.ACCOUNT_ACTIVE
        if utils.is_usable_password_hash(user.hashed_password)
        else auth_service.ACCOUNT_PENDING
    )
    db.commit()
    db.refresh(user)
    return user


# =========================
# Students
# =========================
@router.get("/students", response_model=List[schemas.UserOut])
def list_students(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    users = (
        db.query(models.User)
        .filter(models.User.role == "student")
        .order_by(models.User.name)
        .all()
    )
    return [_user_out(user) for user in users]


@router.get("/students/{student_id}", response_model=schemas.UserOut)
def get_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return _user_out(_get_role_user(db, student_id, "student"))


@router.post("/students", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: schemas.AdminUserCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    if payload.employee_code is not None:
        raise HTTPException(status_code=422, detail="employee_code is not valid for students")
    roll_number = _normalized_identifier(
        db,
        column=models.User.roll_number,
        value=payload.roll_number,
        required_detail="roll_number is required for students",
        duplicate_detail="Roll number already exists",
    )
    try:
        institutional_email = management_service.ensure_unique_email(db, str(payload.email) if payload.email else None)
        institutional_mobile = management_service.ensure_unique_mobile(db, payload.mobile_number)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
    if payload.department is not None or payload.designation is not None or payload.employment_status is not None:
        raise HTTPException(status_code=422, detail="Faculty employment fields are not valid for students")
    user = models.User(
        name=payload.name.strip(),
        email=None,
        institutional_email=institutional_email,
        institutional_mobile=institutional_mobile,
        hashed_password=None,
        role="student",
        roll_number=roll_number,
        photo_url=payload.photo_url,
        is_active=True,
        account_status=auth_service.ACCOUNT_PENDING,
        email_verified=False,
        mobile_verified=False,
        mobile_is_personal=payload.mobile_is_personal,
        college=management_service.clean_optional_text(payload.college),
        academic_program=management_service.clean_optional_text(payload.academic_program),
        admission_year=payload.admission_year,
        present_year=payload.present_year,
        academic_status=payload.academic_status or "ACTIVE",
    )
    return _commit_identifier_user(
        db,
        user,
        "Roll number already exists",
        actor=current_admin,
        action="student.create",
        target_type="student",
        changed_fields=list(payload.model_fields_set),
    )


@router.put("/students/{student_id}", response_model=schemas.UserOut)
def update_student(
    student_id: int,
    payload: schemas.AdminUserUpdate,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    user = _get_role_user(db, student_id, "student")
    registration_complete = _registration_complete(user)
    was_active = user.is_active
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    mobile = data.pop("mobile_number", None)
    email = data.pop("email", None)
    roll_number = data.pop("roll_number", None) if "roll_number" in data else None
    roll_number_supplied = "roll_number" in payload.model_fields_set
    employee_code = data.pop("employee_code", None) if "employee_code" in data else None
    if employee_code is not None:
        raise HTTPException(status_code=422, detail="employee_code is not valid for students")
    for invalid_field in ("department", "designation", "employment_status"):
        if data.get(invalid_field) is not None:
            raise HTTPException(status_code=422, detail=f"{invalid_field} is not valid for students")
    if roll_number_supplied:
        user.roll_number = _normalized_identifier(
            db,
            column=models.User.roll_number,
            value=roll_number,
            required_detail="roll_number is required for students",
            duplicate_detail="Roll number already exists",
            exclude_user_id=user.id,
        )
    if email is not None:
        try:
            normalized_email = management_service.ensure_unique_email(db, str(email), exclude_user_id=user.id)
        except ValueError as exc:
            raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
        current_email = user.email or user.institutional_email
        if registration_complete and normalized_email != current_email:
            raise HTTPException(status_code=409, detail="Verified email changes require account verification")
        user.institutional_email = normalized_email
    if mobile is not None:
        try:
            normalized_mobile = management_service.ensure_unique_mobile(db, mobile, exclude_user_id=user.id)
        except ValueError as exc:
            raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
        current_mobile = user.mobile_number or user.institutional_mobile
        if registration_complete and normalized_mobile != current_mobile:
            raise HTTPException(status_code=409, detail="Verified mobile changes require account verification")
        user.institutional_mobile = normalized_mobile
    for key, value in data.items():
        if key in {"name", "college", "academic_program"} and value is not None:
            value = management_service.clean_optional_text(value)
        setattr(user, key, value)
    if was_active is True and user.is_active is False:
        user.session_version = (user.session_version or 1) + 1
    if not registration_complete:
        user.account_status = auth_service.ACCOUNT_PENDING
        user.email_verified = False
        user.mobile_verified = False
    if password:
        if not registration_complete:
            raise HTTPException(status_code=409, detail="Pending accounts must complete controlled registration")
        secret = password.get_secret_value()
        try:
            utils.validate_password(secret)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        user.hashed_password = utils.hash_password(secret)
        user.session_version = (user.session_version or 1) + 1
    return _commit_identifier_user(
        db,
        user,
        "Roll number already exists",
        actor=current_admin,
        action="student.update",
        target_type="student",
        changed_fields=list(payload.model_fields_set),
    )


@router.post("/students/{student_id}/photo")
async def upload_student_photo(
    student_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    return await _upload_role_photo(
        db=db, actor=current_admin, user_id=student_id, role="student", photo=photo
    )


@router.delete("/students/{student_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_photo(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    return _remove_role_photo(db=db, actor=current_admin, user_id=student_id, role="student")


@router.post("/students/{student_id}/deactivate", response_model=schemas.UserOut)
def deactivate_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    user = _get_role_user(db, student_id, "student")
    user.is_active = False
    user.academic_status = "INACTIVE"
    user.session_version = (user.session_version or 1) + 1
    management_service.record_audit(db, current_admin, action="student.deactivate", target_type="student", target_id=user.id, summary="Student record deactivated", changed_fields=["is_active", "academic_status"])
    db.commit()
    db.refresh(user)
    return user


@router.post("/students/{student_id}/activate", response_model=schemas.UserOut)
def activate_student(
    student_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    user = _get_role_user(db, student_id, "student")
    user.is_active = True
    user.academic_status = "ACTIVE"
    management_service.record_audit(db, current_admin, action="student.activate", target_type="student", target_id=user.id, summary="Student record activated", changed_fields=["is_active", "academic_status"])
    db.commit()
    db.refresh(user)
    return user


# =========================
# Faculty
# =========================
@router.get("/faculty", response_model=List[schemas.UserOut])
def list_faculty(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    users = (
        db.query(models.User)
        .filter(models.User.role == "faculty")
        .order_by(models.User.name)
        .all()
    )
    return [_user_out(user) for user in users]


@router.get("/faculty/{faculty_id}", response_model=schemas.FacultyResponsibilitiesOut)
def get_faculty(
    faculty_id: int,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    registration_complete = _registration_complete(user)
    coords = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.faculty_id == faculty_id)
        .all()
    )
    experts = (
        db.query(models.SubjectExpertAssignment)
        .filter(models.SubjectExpertAssignment.faculty_id == faculty_id)
        .all()
    )
    return schemas.FacultyResponsibilitiesOut(
        faculty=_user_out(user),
        course_coordinator_assignments=[_coordinator_out(r) for r in coords],
        subject_expert_assignments=[_expert_out(r) for r in experts],
    )


@router.post("/faculty", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: schemas.AdminUserCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    if payload.roll_number is not None:
        raise HTTPException(status_code=422, detail="roll_number is not valid for faculty")
    employee_code = _normalized_identifier(
        db,
        column=models.User.employee_code,
        value=payload.employee_code,
        required_detail="employee_code is required for faculty",
        duplicate_detail="Employee code already exists",
    )
    try:
        institutional_email = management_service.ensure_unique_email(db, str(payload.email) if payload.email else None)
        institutional_mobile = management_service.ensure_unique_mobile(db, payload.mobile_number)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
    if payload.academic_program is not None or payload.admission_year is not None or payload.present_year is not None or payload.academic_status is not None:
        raise HTTPException(status_code=422, detail="Student academic fields are not valid for faculty")
    user = models.User(
        name=payload.name.strip(),
        email=None,
        institutional_email=institutional_email,
        institutional_mobile=institutional_mobile,
        hashed_password=None,
        role="faculty",
        employee_code=employee_code,
        photo_url=payload.photo_url,
        is_active=True,
        account_status=auth_service.ACCOUNT_PENDING,
        email_verified=False,
        mobile_verified=False,
        mobile_is_personal=payload.mobile_is_personal,
        college=management_service.clean_optional_text(payload.college),
        department=management_service.clean_optional_text(payload.department),
        designation=management_service.clean_optional_text(payload.designation),
        employment_status=payload.employment_status or "ACTIVE",
    )
    return _commit_identifier_user(
        db,
        user,
        "Employee code already exists",
        actor=current_admin,
        action="faculty.create",
        target_type="faculty",
        changed_fields=list(payload.model_fields_set),
    )


@router.put("/faculty/{faculty_id}", response_model=schemas.UserOut)
def update_faculty(
    faculty_id: int,
    payload: schemas.AdminUserUpdate,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    was_active = user.is_active
    data = payload.model_dump(exclude_unset=True)
    password = data.pop("password", None)
    mobile = data.pop("mobile_number", None)
    email = data.pop("email", None)
    employee_code = data.pop("employee_code", None) if "employee_code" in data else None
    employee_code_supplied = "employee_code" in payload.model_fields_set
    roll_number = data.pop("roll_number", None) if "roll_number" in data else None
    if roll_number is not None:
        raise HTTPException(status_code=422, detail="roll_number is not valid for faculty")
    for invalid_field in ("academic_program", "admission_year", "present_year", "academic_status"):
        if data.get(invalid_field) is not None:
            raise HTTPException(status_code=422, detail=f"{invalid_field} is not valid for faculty")
    if employee_code_supplied:
        user.employee_code = _normalized_identifier(
            db,
            column=models.User.employee_code,
            value=employee_code,
            required_detail="employee_code is required for faculty",
            duplicate_detail="Employee code already exists",
            exclude_user_id=user.id,
        )
    if email is not None:
        try:
            normalized_email = management_service.ensure_unique_email(db, str(email), exclude_user_id=user.id)
        except ValueError as exc:
            raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
        current_email = user.email or user.institutional_email
        if registration_complete and normalized_email != current_email:
            raise HTTPException(status_code=409, detail="Verified email changes require account verification")
        user.institutional_email = normalized_email
    if mobile is not None:
        try:
            normalized_mobile = management_service.ensure_unique_mobile(db, mobile, exclude_user_id=user.id)
        except ValueError as exc:
            raise HTTPException(status_code=409 if "exists" in str(exc) else 422, detail=str(exc))
        current_mobile = user.mobile_number or user.institutional_mobile
        if registration_complete and normalized_mobile != current_mobile:
            raise HTTPException(status_code=409, detail="Verified mobile changes require account verification")
        user.institutional_mobile = normalized_mobile
    for key, value in data.items():
        if key in {"name", "college", "department", "designation"} and value is not None:
            value = management_service.clean_optional_text(value)
        setattr(user, key, value)
    if was_active is True and user.is_active is False:
        user.session_version = (user.session_version or 1) + 1
    if not registration_complete:
        user.account_status = auth_service.ACCOUNT_PENDING
        user.email_verified = False
        user.mobile_verified = False
    if password:
        if not registration_complete:
            raise HTTPException(status_code=409, detail="Pending accounts must complete controlled registration")
        secret = password.get_secret_value()
        try:
            utils.validate_password(secret)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        user.hashed_password = utils.hash_password(secret)
        user.session_version = (user.session_version or 1) + 1
    return _commit_identifier_user(
        db,
        user,
        "Employee code already exists",
        actor=current_admin,
        action="faculty.update",
        target_type="faculty",
        changed_fields=list(payload.model_fields_set),
    )


@router.post("/faculty/{faculty_id}/photo")
async def upload_faculty_photo(
    faculty_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    return await _upload_role_photo(
        db=db, actor=current_admin, user_id=faculty_id, role="faculty", photo=photo
    )


@router.delete("/faculty/{faculty_id}/photo", status_code=status.HTTP_204_NO_CONTENT)
def remove_faculty_photo(
    faculty_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    return _remove_role_photo(db=db, actor=current_admin, user_id=faculty_id, role="faculty")


@router.post("/faculty/{faculty_id}/deactivate", response_model=schemas.UserOut)
def deactivate_faculty(
    faculty_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    user.is_active = False
    user.employment_status = "INACTIVE"
    user.session_version = (user.session_version or 1) + 1
    management_service.record_audit(db, current_admin, action="faculty.deactivate", target_type="faculty", target_id=user.id, summary="Faculty record deactivated", changed_fields=["is_active", "employment_status"])
    db.commit()
    db.refresh(user)
    return user


@router.post("/faculty/{faculty_id}/activate", response_model=schemas.UserOut)
def activate_faculty(
    faculty_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    user = _get_role_user(db, faculty_id, "faculty")
    user.is_active = True
    user.employment_status = "ACTIVE"
    management_service.record_audit(db, current_admin, action="faculty.activate", target_type="faculty", target_id=user.id, summary="Faculty record activated", changed_fields=["is_active", "employment_status"])
    db.commit()
    db.refresh(user)
    return user


# =========================
# Subjects (minimal)
# =========================
@router.get("/subjects", response_model=List[schemas.SubjectOut])
def list_subjects(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    return db.query(models.Subject).order_by(models.Subject.sequence, models.Subject.name).all()


@router.post("/subjects", response_model=schemas.SubjectOut, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: schemas.SubjectCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    if payload.course_id is not None:
        from app.services.syllabus_review import guard_legacy_write
        guard_legacy_write(db, payload.course_id)
        course = db.query(models.Course).filter(models.Course.id == payload.course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
    if db.query(models.Subject).filter(models.Subject.course_id == payload.course_id, models.Subject.name == payload.name.strip()).first():
        raise HTTPException(status_code=409, detail="Subject name already exists in this course")
    subject = models.Subject(
        name=payload.name.strip(),
        description=payload.description,
        course_id=payload.course_id,
    )
    db.add(subject)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Subject name already exists in this course")
    db.refresh(subject)
    return subject


@router.get("/courses/{course_id}/syllabus")
def get_course_syllabus(course_id: int, db: Session = Depends(database.get_db), _: models.User = Depends(_admin)):
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    subjects = db.query(models.Subject).filter(models.Subject.course_id == course_id).order_by(models.Subject.sequence, models.Subject.name).all()
    return {"course_id": course.id, "course_title": course.title, "subjects": [{"id": subject.id, "name": subject.name, "description": subject.description, "units": [{"id": unit.id, "name": unit.name, "description": unit.description, "sequence": unit.sequence, "topics": [{"id": topic.id, "name": topic.name, "description": topic.description, "subtopics": [{"id": row.id, "name": row.name, "description": row.description} for row in sorted(topic.subtopics, key=lambda item: (item.sequence, item.name.lower()))]} for topic in sorted(unit.topics, key=lambda item: (item.sequence, item.name.lower()))]} for unit in sorted(subject.units, key=lambda item: (item.sequence, item.name.lower()))]} for subject in subjects]}


@router.post("/units", response_model=schemas.UnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(payload: schemas.UnitCreate, db: Session = Depends(database.get_db), _: models.User = Depends(_admin)):
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    from app.services.syllabus_review import guard_legacy_write
    guard_legacy_write(db, subject.course_id)
    duplicate = db.query(models.Unit).filter(models.Unit.subject_id == subject.id, models.Unit.name == payload.name.strip()).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Unit name already exists in this subject")
    row = models.Unit(subject_id=subject.id, name=payload.name.strip(), description=payload.description, sequence=payload.sequence)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.post("/courses/{course_id}/syllabus/import")
def import_course_syllabus(course_id: int, payload: schemas.SyllabusImportRequest, db: Session = Depends(database.get_db), current_admin: models.User = Depends(_admin)):
    from app.services.syllabus_review import guard_legacy_write
    guard_legacy_write(db, course_id)
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    created = {"subjects": 0, "units": 0, "topics": 0, "subtopics": 0}
    try:
        for item in payload.rows:
            subject_name, unit_name, topic_name = item.subject.strip(), item.unit.strip(), item.topic.strip()
            subject = db.query(models.Subject).filter(models.Subject.course_id == course_id, models.Subject.name == subject_name).first()
            if not subject:
                subject = models.Subject(course_id=course_id, name=subject_name, description=item.subject_description)
                db.add(subject); db.flush(); created["subjects"] += 1
            unit = db.query(models.Unit).filter(models.Unit.subject_id == subject.id, models.Unit.name == unit_name).first()
            if not unit:
                unit = models.Unit(subject_id=subject.id, name=unit_name, description=item.unit_description, sequence=item.unit_sequence)
                db.add(unit); db.flush(); created["units"] += 1
            topic = db.query(models.Topic).filter(models.Topic.subject_id == subject.id, models.Topic.unit_id == unit.id, models.Topic.name == topic_name).first()
            if not topic:
                topic = models.Topic(subject_id=subject.id, unit_id=unit.id, name=topic_name, description=item.topic_description)
                db.add(topic); db.flush(); created["topics"] += 1
            if item.subtopic and item.subtopic.strip():
                name = item.subtopic.strip()
                if not db.query(models.Subtopic).filter(models.Subtopic.topic_id == topic.id, models.Subtopic.name == name).first():
                    db.add(models.Subtopic(topic_id=topic.id, name=name, description=item.subtopic_description)); created["subtopics"] += 1
        db.add(models.AdminAuditLog(actor_user_id=current_admin.id, action="syllabus.import", target_type="course", target_id=course_id, summary=f"Imported syllabus for {course.title}", details={"rows": len(payload.rows), **created}))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"course_id": course_id, "processed_rows": len(payload.rows), "created": created}


@router.put("/courses/{course_id}/syllabus/{level}/{item_id}")
def update_course_syllabus_item(course_id: int, level: str, item_id: int, payload: schemas.SyllabusItemUpdate, db: Session = Depends(database.get_db), current_admin: models.User = Depends(_admin)):
    from app.services.syllabus_review import guard_legacy_write
    guard_legacy_write(db, course_id)
    model = {"subject": models.Subject, "unit": models.Unit, "topic": models.Topic, "subtopic": models.Subtopic}.get(level)
    if model is None:
        raise HTTPException(status_code=422, detail="Unknown syllabus hierarchy level")
    item = db.query(model).filter(model.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Syllabus item not found")
    owner_course_id = item.course_id if level == "subject" else item.subject.course_id if level == "unit" else item.subject.course_id if level == "topic" else item.topic.subject.course_id
    if owner_course_id != course_id:
        raise HTTPException(status_code=404, detail="Syllabus item does not belong to this course")
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Syllabus item name cannot be blank")
    if level == "subject":
        duplicate = db.query(models.Subject).filter(models.Subject.course_id == course_id, models.Subject.name == name, models.Subject.id != item_id).first()
    elif level == "unit":
        duplicate = db.query(models.Unit).filter(models.Unit.subject_id == item.subject_id, models.Unit.name == name, models.Unit.id != item_id).first()
    elif level == "topic":
        duplicate = db.query(models.Topic).filter(models.Topic.unit_id == item.unit_id, models.Topic.name == name, models.Topic.id != item_id).first()
    else:
        duplicate = db.query(models.Subtopic).filter(models.Subtopic.topic_id == item.topic_id, models.Subtopic.name == name, models.Subtopic.id != item_id).first()
    if duplicate:
        raise HTTPException(status_code=409, detail=f"A {level} with this name already exists in the same hierarchy")
    item.name = name
    item.description = payload.description
    if level == "unit" and payload.sequence is not None:
        item.sequence = payload.sequence
    db.add(models.AdminAuditLog(actor_user_id=current_admin.id, action="syllabus.update", target_type=level, target_id=item.id, summary=f"Updated {level}: {name}", details={"course_id": course_id}))
    db.commit()
    return {"id": item.id, "level": level, "name": item.name, "description": item.description}


# =========================
# Hierarchical academic weightages
# =========================
def _weightage_scope(db: Session, course_id: int, actor: models.User) -> dict:
    course = db.query(models.Course).filter(models.Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    role = str(actor.role or "").lower()
    if role in {"admin", "super_admin"}:
        return {"course": course, "can_manage_course": True, "subject_ids": None, "actor_role": role}
    coordinator = db.query(models.FacultyCourseAssignment.id).filter(models.FacultyCourseAssignment.course_id == course_id, models.FacultyCourseAssignment.faculty_id == actor.id).first()
    if coordinator:
        return {"course": course, "can_manage_course": True, "subject_ids": None, "actor_role": role}
    subject_ids = {row[0] for row in db.query(models.SubjectExpertAssignment.subject_id).join(models.Subject, models.Subject.id == models.SubjectExpertAssignment.subject_id).filter(models.Subject.course_id == course_id, models.SubjectExpertAssignment.faculty_id == actor.id).all()}
    if not subject_ids:
        raise HTTPException(status_code=403, detail="Academic responsibility for this course is required")
    return {"course": course, "can_manage_course": False, "subject_ids": subject_ids, "actor_role": role}


def _academic_weight_tree(db: Session, course_id: int, scope: dict) -> dict:
    subjects = db.query(models.Subject).filter(models.Subject.course_id == course_id).order_by(models.Subject.sequence, models.Subject.name).all()
    subject_weights = {row.subject_id: row.weight_percent for row in db.query(models.SubjectWeightage).filter(models.SubjectWeightage.course_id == course_id).all()}
    subject_ids = [item.id for item in subjects]
    unit_weights = {row.unit_id: row.weight_percent for row in db.query(models.UnitWeightage).filter(models.UnitWeightage.subject_id.in_(subject_ids)).all()} if subject_ids else {}
    topic_weights = {row.topic_id: row.weight_percent for row in db.query(models.TopicWeightage).filter(models.TopicWeightage.subject_id.in_(subject_ids)).all()} if subject_ids else {}
    topic_ids = [topic.id for subject in subjects for unit in subject.units for topic in unit.topics]
    subtopic_weights = {row.subtopic_id: row.weight_percent for row in db.query(models.SubtopicWeightage).filter(models.SubtopicWeightage.topic_id.in_(topic_ids)).all()} if topic_ids else {}
    visible = []
    for subject in subjects:
        editable = scope["can_manage_course"] or subject.id in (scope["subject_ids"] or set())
        visible.append({"id": subject.id, "name": subject.name, "weight_percent": subject_weights.get(subject.id), "editable": editable, "units": [{"id": unit.id, "name": unit.name, "sequence": unit.sequence, "weight_percent": unit_weights.get(unit.id), "topics": [{"id": topic.id, "name": topic.name, "weight_percent": topic_weights.get(topic.id), "subtopics": [{"id": subtopic.id, "name": subtopic.name, "weight_percent": subtopic_weights.get(subtopic.id)} for subtopic in sorted(topic.subtopics, key=lambda item: (item.sequence, item.name.lower()))]} for topic in sorted(unit.topics, key=lambda item: (item.sequence, item.name.lower()))]} for unit in sorted(subject.units, key=lambda item: (item.sequence, item.name.lower()))]})
    configured = {"subjects": len(subject_weights), "units": len(unit_weights), "topics": len(topic_weights), "subtopics": len(subtopic_weights)}
    tree = {"course_id": course_id, "course_title": scope["course"].title, "can_manage_course": scope["can_manage_course"],
        "actor_role": scope["actor_role"], "can_final_approve": scope["actor_role"] in {"admin", "super_admin"},
        "editable_subject_ids": None if scope["can_manage_course"] else sorted(scope["subject_ids"]), "configured": configured, "subjects": visible}
    from app.services import weightage_governance
    for subject in visible:
        subject["governance"] = weightage_governance.serialize(db, tree, subject)
    tree["coordinator_readiness_status"] = scope["course"].coordinator_readiness_status
    return tree


def _publication_readiness(db: Session, course_id: int, scope: dict) -> dict:
    from app.services.syllabus_subjects import publication_ready
    from app.services import weightage_governance
    tree = _academic_weight_tree(db, course_id, scope)
    course, subjects = scope["course"], tree["subjects"]
    coordinators = db.query(models.FacultyCourseAssignment).filter(models.FacultyCourseAssignment.course_id == course_id).all()
    experts = db.query(models.SubjectExpertAssignment).join(models.Subject).filter(models.Subject.course_id == course_id).all()
    active_coordinators = [item for item in coordinators if item.faculty and item.faculty.is_active]
    expert_subjects = {item.subject_id for item in experts if item.faculty and item.faculty.is_active}
    def weighted(items):
        return bool(items) and all(item.get("weight_percent") is not None for item in items) and isclose(sum(item["weight_percent"] for item in items), 100.0, abs_tol=0.01)
    hierarchy = bool(subjects) and all(subject["units"] and all(unit["topics"] for unit in subject["units"]) for subject in subjects)
    deeper = bool(subjects) and all(weighted(subject["units"]) and all(weighted(unit["topics"]) and all(not topic["subtopics"] or weighted(topic["subtopics"]) for topic in unit["topics"]) for unit in subject["units"]) for subject in subjects)
    checks = [
        {"key": "syllabus_approval", "label": "All subject syllabuses finally approved", "complete": publication_ready(db, course), "detail": "Every subject syllabus needs expert recommendation and administrator final approval.", "href": f"/admin/courses/{course_id}/syllabus/reviews"},
        {"key": "weightage_approval", "label": "All subject weightages finally approved", "complete": weightage_governance.all_approved(db, tree), "detail": "Every complete subject weightage snapshot needs expert recommendation and administrator final approval.", "href": f"/admin/courses/{course_id}/weightages"},
        {"key": "coordinator_readiness", "label": "Course Coordinator readiness", "complete": course.coordinator_readiness_status == "CONFIRMED", "detail": "An active assigned Course Coordinator must confirm complete-course readiness.", "href": f"/admin/courses/{course_id}/syllabus/reviews"},
        {"key": "identity", "label": "Course identity and examination information", "complete": bool(course.title and course.programme_code and course.examination_name and course.examination_authority), "detail": "Course title, code, examination name and examination authority must be configured.", "href": f"/admin/courses/{course_id}/edit"},
        {"key": "syllabus", "label": "Structured syllabus", "complete": hierarchy, "detail": "Every subject requires a unit and every unit requires a topic.", "href": f"/admin/courses/{course_id}/syllabus"},
        {"key": "coordinator", "label": "Active course coordinator", "complete": bool(active_coordinators), "detail": "Assign at least one active course coordinator.", "href": f"/admin/academic-responsibilities?course_id={course_id}"},
        {"key": "experts", "label": "Subject experts", "complete": bool(subjects) and all(subject["id"] in expert_subjects for subject in subjects), "detail": "Assign an active subject expert to every subject.", "href": f"/admin/academic-responsibilities?course_id={course_id}"},
        {"key": "subjects", "label": "Subject weightages", "complete": weighted(subjects), "detail": "Subject weightages must total 100%.", "href": f"/admin/courses/{course_id}/weightages"},
        {"key": "weights", "label": "Unit, topic and subtopic weightages", "complete": deeper, "detail": "Every applicable unit, topic and subtopic group must total 100%.", "href": f"/admin/courses/{course_id}/weightages"},
    ]
    complete = sum(item["complete"] for item in checks)
    pending_count = db.query(models.StudentCourseEnrollment).filter_by(course_id=course_id, status="PENDING_ACTIVATION").count()
    return {"course_id": course_id, "publication_status": course.publication_status, "pending_enrollment_count": pending_count, "ready": complete == len(checks), "completed": complete, "total": len(checks), "percent": round(complete / len(checks) * 100), "checks": checks, "pending_actions": [item for item in checks if not item["complete"]]}


@router.get("/courses/{course_id}/publication-readiness")
def get_course_publication_readiness(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    scope = _weightage_scope(db, course_id, actor)
    if not scope["can_manage_course"]:
        raise HTTPException(status_code=403, detail="Full course readiness requires coordinator responsibility")
    return _publication_readiness(db, course_id, scope)


@router.post("/courses/{course_id}/submit-for-review")
def submit_course_for_review(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    scope = _weightage_scope(db, course_id, actor)
    if not scope["can_manage_course"]:
        raise HTTPException(status_code=403, detail="Only a course coordinator or administrator can submit a course for review")
    readiness = _publication_readiness(db, course_id, scope)
    if not readiness["ready"]:
        raise HTTPException(status_code=409, detail="Complete every publication readiness requirement before submitting for review")
    course = scope["course"]
    course.publication_status, course.is_active = "READY_FOR_REVIEW", False
    course.submitted_for_review_at, course.submitted_for_review_by = datetime.now(timezone.utc), actor.id
    management_service.record_audit(db, actor, action="course.submit_for_review", target_type="course", target_id=course_id, summary=f"Submitted {course.title} for review", changed_fields=["publication_status"])
    db.commit()
    return _publication_readiness(db, course_id, scope)


@router.post("/courses/{course_id}/publish")
def publish_course(course_id: int, payload: schemas.CoursePublishRequest = None, db: Session = Depends(database.get_db), actor: models.User = Depends(_admin)):
    from app.services import course_enrollments as enrollment_service
    from app.services.syllabus_subjects import finalize_for_publication
    db.query(models.Course).filter_by(id=course_id).with_for_update().first()
    finalize_for_publication(db, actor, db.get(models.Course, course_id))
    scope = _weightage_scope(db, course_id, actor)
    if not _publication_readiness(db, course_id, scope)["ready"]:
        raise HTTPException(status_code=409, detail="Complete every publication readiness requirement before publishing")
    course = scope["course"]
    if course.publication_status == "ARCHIVED":
        raise HTTPException(409, "Return the archived course to draft and review before publishing")
    pending_count = db.query(models.StudentCourseEnrollment).filter_by(course_id=course_id, status="PENDING_ACTIVATION").count()
    if payload and payload.activate_pending and payload.expected_pending_count != pending_count:
        raise HTTPException(409, "Pending assignments changed; refresh and confirm the current count")
    course.publication_status, course.is_active = "PUBLISHED", True
    course.published_at, course.published_by = datetime.now(timezone.utc), actor.id
    syllabus_version = db.query(models.SyllabusRevision).filter_by(course_id=course_id, number=course.syllabus_revision).first()
    if syllabus_version and not syllabus_version.published_at: syllabus_version.published_at = course.published_at
    course.archived_at, course.archived_by = None, None
    activation = enrollment_service.activate_pending(db, course, actor) if payload and payload.activate_pending else {"activated": 0, "skipped": 0}
    management_service.record_audit(db, actor, action="course.publish", target_type="course", target_id=course_id, summary=f"Published {course.title}", changed_fields=["publication_status", "is_active"])
    db.commit()
    return {**_publication_readiness(db, course_id, scope), "enrollment_activation": activation}


@router.post("/courses/{course_id}/return-to-draft")
def return_course_to_draft(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_admin)):
    scope = _weightage_scope(db, course_id, actor)
    course = scope["course"]
    course.publication_status, course.is_active = "DRAFT", False
    management_service.record_audit(db, actor, action="course.return_to_draft", target_type="course", target_id=course_id, summary=f"Returned {course.title} to draft", changed_fields=["publication_status", "is_active"])
    db.commit()
    return _publication_readiness(db, course_id, scope)


@router.post("/courses/{course_id}/archive")
def archive_course(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_admin)):
    scope = _weightage_scope(db, course_id, actor)
    course = scope["course"]
    course.publication_status, course.is_active = "ARCHIVED", False
    course.archived_at, course.archived_by = datetime.now(timezone.utc), actor.id
    management_service.record_audit(db, actor, action="course.archive", target_type="course", target_id=course_id, summary=f"Archived {course.title}", changed_fields=["publication_status", "is_active"])
    db.commit()
    return _publication_readiness(db, course_id, scope)


@router.get("/courses/{course_id}/weightages")
def get_course_academic_weightages(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    return _academic_weight_tree(db, course_id, _weightage_scope(db, course_id, actor))


@router.put("/courses/{course_id}/weightages")
def update_course_academic_weightages(course_id: int, payload: schemas.AcademicWeightageGroupUpdate, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    scope = _weightage_scope(db, course_id, actor)
    ids = [item.item_id for item in payload.items]
    if len(set(ids)) != len(ids):
        raise HTTPException(status_code=422, detail="Each syllabus item can appear only once in a weightage group")
    total = sum(item.weight_percent for item in payload.items)
    if not isclose(total, 100.0, rel_tol=0.0, abs_tol=0.01):
        raise HTTPException(status_code=422, detail=f"Weightages must total exactly 100%; received {round(total, 2)}%")

    if payload.level == "subject":
        if payload.parent_id != course_id:
            raise HTTPException(status_code=404, detail="Subject group does not belong to this course")
        if not scope["can_manage_course"]:
            raise HTTPException(status_code=403, detail="Only a course coordinator or administrator can edit subject weightages")
        children = db.query(models.Subject).filter(models.Subject.course_id == course_id).all()
        model, owner_field, child_field, owner_id = models.SubjectWeightage, "course_id", "subject_id", course_id
    elif payload.level == "unit":
        subject = db.query(models.Subject).filter(models.Subject.id == payload.parent_id, models.Subject.course_id == course_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject does not belong to this course")
        if not scope["can_manage_course"] and subject.id not in scope["subject_ids"]:
            raise HTTPException(status_code=403, detail="Subject expert responsibility is required for this subject")
        children, model, owner_field, child_field, owner_id = list(subject.units), models.UnitWeightage, "subject_id", "unit_id", subject.id
    elif payload.level == "topic":
        unit = db.query(models.Unit).filter(models.Unit.id == payload.parent_id).first()
        if not unit or unit.subject.course_id != course_id:
            raise HTTPException(status_code=404, detail="Unit does not belong to this course")
        if not scope["can_manage_course"] and unit.subject_id not in scope["subject_ids"]:
            raise HTTPException(status_code=403, detail="Subject expert responsibility is required for this subject")
        children, model, owner_field, child_field, owner_id = list(unit.topics), models.TopicWeightage, "subject_id", "topic_id", unit.subject_id
    else:
        topic = db.query(models.Topic).filter(models.Topic.id == payload.parent_id).first()
        if not topic or topic.subject.course_id != course_id:
            raise HTTPException(status_code=404, detail="Topic does not belong to this course")
        if not scope["can_manage_course"] and topic.subject_id not in scope["subject_ids"]:
            raise HTTPException(status_code=403, detail="Subject expert responsibility is required for this subject")
        children, model, owner_field, child_field, owner_id = list(topic.subtopics), models.SubtopicWeightage, "topic_id", "subtopic_id", topic.id

    expected_ids = {item.id for item in children}
    if not expected_ids:
        raise HTTPException(status_code=422, detail="Add syllabus items before configuring their weightages")
    if set(ids) != expected_ids:
        raise HTTPException(status_code=422, detail="Weightages must include every item in the selected sibling group")
    existing = {getattr(row, child_field): row for row in db.query(model).filter(getattr(model, child_field).in_(ids)).all()}
    for item in payload.items:
        row = existing.get(item.item_id)
        if row:
            row.weight_percent = item.weight_percent
        else:
            db.add(model(**{owner_field: owner_id, child_field: item.item_id, "weight_percent": item.weight_percent}))
    from app.services import weightage_governance
    affected_subject_ids = [item.id for item in children] if payload.level == "subject" else [owner_id if payload.level == "unit" else unit.subject_id if payload.level == "topic" else topic.subject_id]
    weightage_governance.invalidate(db, scope["course"], affected_subject_ids)
    management_service.record_audit(db, actor, action=f"weightage.{payload.level}.update", target_type="course", target_id=course_id, summary=f"Updated {payload.level} weightages for {scope['course'].title}", changed_fields=[f"{payload.level}_weightages"])
    db.commit()
    return {"course_id": course_id, "level": payload.level, "parent_id": payload.parent_id, "total_percent": round(total, 2), "updated": len(payload.items), "message": f"{payload.level.capitalize()} weightages saved successfully"}


@router.post("/courses/{course_id}/weightages/{subject_id}/governance")
def weightage_governance_action(course_id: int, subject_id: int, payload: schemas.WeightageGovernanceAction,
        db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    from app.services import weightage_governance
    scope = _weightage_scope(db, course_id, actor)
    course = db.query(models.Course).filter_by(id=course_id).with_for_update().first()
    subject = db.query(models.Subject).filter_by(id=subject_id, course_id=course_id).first()
    if not subject: raise HTTPException(404, "Subject does not belong to this course")
    tree = _academic_weight_tree(db, course_id, scope)
    row = weightage_governance.act(db, actor, course, subject, tree, payload.action, payload.version, payload.comment)
    management_service.record_audit(db, actor, action=f"weightage.governance.{payload.action}", target_type="subject", target_id=subject_id,
        summary=f"{payload.action.capitalize()} weightages for {subject.name}", changed_fields=["weightage_approval_status"])
    db.commit()
    tree = _academic_weight_tree(db, course_id, scope)
    return weightage_governance.serialize(db, tree, next(item for item in tree["subjects"] if item["id"] == subject_id))


def _current_subject_tasks(db, course):
    review = db.query(models.SyllabusReview).filter_by(course_id=course.id).order_by(models.SyllabusReview.id.desc()).first()
    return db.query(models.SyllabusSubjectReview).filter_by(review_id=review.id).all() if review else []


@router.post("/courses/{course_id}/coordinator-readiness")
def coordinator_readiness(course_id: int, payload: schemas.CoordinatorReadinessAction,
        db: Session = Depends(database.get_db), actor: models.User = Depends(_faculty)):
    from app.academic_auth import is_course_coordinator
    from app.services import weightage_governance
    course = db.query(models.Course).filter_by(id=course_id).with_for_update().first()
    if not course: raise HTTPException(404, "Course not found")
    if not is_course_coordinator(db, actor, course_id): raise HTTPException(403, "Assigned Course Coordinator required")
    scope = _weightage_scope(db, course_id, actor); tree = _academic_weight_tree(db, course_id, scope)
    if payload.action == "confirm":
        if not weightage_governance.all_recommended_or_approved(db, course, tree, _current_subject_tasks(db, course)):
            raise HTTPException(409, "Every subject syllabus and complete weightage snapshot must be recommended or approved")
        course.coordinator_readiness_status = "CONFIRMED"
        course.coordinator_confirmed_by = actor.id; course.coordinator_confirmed_at = datetime.now(timezone.utc)
    else:
        course.coordinator_readiness_status = "PENDING"
        course.coordinator_confirmed_by = course.coordinator_confirmed_at = None
    management_service.record_audit(db, actor, action=f"course.coordinator_readiness.{payload.action}", target_type="course", target_id=course_id,
        summary=f"Course Coordinator {payload.action}: {course.title}", changed_fields=["coordinator_readiness_status"])
    db.commit()
    return {"course_id": course_id, "coordinator_readiness_status": course.coordinator_readiness_status}


@router.post("/courses/{course_id}/approve-all-eligible-subjects")
def approve_all_eligible_subjects(course_id: int, payload: schemas.BulkSubjectApprovalRequest,
        db: Session = Depends(database.get_db), actor: models.User = Depends(_admin)):
    from app.services import syllabus_subjects, weightage_governance
    course = db.query(models.Course).filter_by(id=course_id).with_for_update().first()
    if not course: raise HTTPException(404, "Course not found")
    if course.coordinator_readiness_status != "CONFIRMED":
        raise HTTPException(409, "Course Coordinator readiness confirmation is required first")
    review = db.query(models.SyllabusReview).filter_by(course_id=course_id).order_by(models.SyllabusReview.id.desc()).first()
    tasks = db.query(models.SyllabusSubjectReview).filter_by(review_id=review.id).all() if review else []
    task_by_subject = {task.live_subject_id: task for task in tasks if task.live_subject_id}
    scope = _weightage_scope(db, course_id, actor); tree = _academic_weight_tree(db, course_id, scope)
    approved, blocked = [], []
    for subject_data in tree["subjects"]:
        subject = db.get(models.Subject, subject_data["id"]); task = task_by_subject.get(subject.id)
        weight = weightage_governance.state(db, course_id, subject.id, create=True)
        weight_view = weightage_governance.serialize(db, tree, subject_data)
        syllabus_eligible = bool(task and task.status in {"RECOMMENDED", "APPROVED"})
        weight_eligible = weight_view["status"] in {"RECOMMENDED", "APPROVED"}
        if not (syllabus_eligible and weight_eligible and weight_view["complete"]):
            blocked.append({"subject_id": subject.id, "subject_name": subject.name,
                "syllabus_status": task.status if task else "MISSING", "weightage_status": weight_view["status"]})
            continue
        if task.status == "RECOMMENDED":
            syllabus_subjects.approve_task(db, actor, course, review, task, payload.comment)
        if weight.status == "RECOMMENDED":
            weightage_governance.act(db, actor, course, subject, tree, "approve", weight.version, payload.comment)
        approved.append({"subject_id": subject.id, "subject_name": subject.name})
    if review and syllabus_subjects.ready(db, review) and review.status != "APPROVED":
        syllabus_subjects.materialize(db, actor, course, review)
    management_service.record_audit(db, actor, action="course.approve_all_eligible_subjects", target_type="course", target_id=course_id,
        summary=f"Approved {len(approved)} eligible subjects for {course.title}", changed_fields=["syllabus_approval", "weightage_approval"])
    db.commit()
    return {"approved": approved, "blocked": blocked, "approved_count": len(approved), "blocked_count": len(blocked)}


# =========================
# Ownership-scoped course and subject PDF reports
# =========================
def _course_report_payload(db: Session, course_id: int, actor: models.User, subject_id: int | None = None) -> dict:
    scope = _weightage_scope(db, course_id, actor)
    if subject_id is None and not scope["can_manage_course"]:
        raise HTTPException(status_code=403, detail="Only an assigned course coordinator or administrator can download the complete course report")
    if subject_id is not None:
        subject = db.query(models.Subject).filter(models.Subject.id == subject_id, models.Subject.course_id == course_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject does not belong to this course")
        if not scope["can_manage_course"] and subject_id not in scope["subject_ids"]:
            raise HTTPException(status_code=403, detail="Subject expert responsibility is required to download this subject report")

    tree = _academic_weight_tree(db, course_id, scope)
    subjects = [row for row in tree["subjects"] if subject_id is None or row["id"] == subject_id]
    subject_ids = [row["id"] for row in subjects]
    coordinators = [{"name": row.faculty.name, "employee_code": row.faculty.employee_code, "department": row.faculty.department, "designation": row.faculty.designation} for row in db.query(models.FacultyCourseAssignment).filter(models.FacultyCourseAssignment.course_id == course_id).all() if row.faculty]
    assignments = db.query(models.SubjectExpertAssignment).join(models.Subject, models.Subject.id == models.SubjectExpertAssignment.subject_id).filter(models.Subject.course_id == course_id)
    if subject_id is not None:
        assignments = assignments.filter(models.SubjectExpertAssignment.subject_id == subject_id)
    experts = [{"name": row.faculty.name, "employee_code": row.faculty.employee_code, "department": row.faculty.department, "designation": row.faculty.designation, "subject_name": row.subject.name, "subject_id": row.subject_id} for row in assignments.all() if row.faculty and row.subject]

    syllabus_status = None
    if subject_id is None and scope['can_manage_course']:
        from app.services.syllabus_configuration import configuration
        saved = configuration(db, scope['course'])
        if saved['review_id']:
            draft = db.get(models.SyllabusReview, saved['review_id'])
            def children(parent, level):
                child_field = {'subject': 'units', 'unit': 'topics', 'topic': 'subtopics'}
                next_level = {'subject': 'unit', 'unit': 'topic', 'topic': 'subtopic'}
                result = []
                for node in sorted(draft.proposed_nodes, key=lambda n: n['sequence']):
                    if node['parent'] != parent or node['level'] != level: continue
                    item = dict(node, id=node['key'], weight_percent=None)
                    if level in child_field:
                        item[child_field[level]] = children(node['key'], next_level[level])
                    result.append(item)
                return result
            subjects = children(None, 'subject')
            experts = []
            for assignment in saved['experts']:
                person = db.get(models.User, assignment['faculty_id'])
                experts.append(dict(name=person.name, employee_code=person.employee_code,
                    department=person.department, designation=person.designation,
                    subject_name=assignment['subject_name'], subject_id=assignment['subject_id']))
            syllabus_status = f"SAVED WORKING SYLLABUS - {saved['approved_subject_count']} of {saved['subject_count']} subjects approved; not published"

    sessions = db.query(models.LearningSession).filter(models.LearningSession.course_id == course_id)
    assessments = db.query(models.Assessment).filter(models.Assessment.course_id == course_id)
    questions = db.query(models.Question).filter(models.Question.course_id == course_id)
    remedial = db.query(models.RemedialGroup).filter(models.RemedialGroup.course_id == course_id)
    attempts = db.query(models.AssessmentAttempt).filter(models.AssessmentAttempt.course_id == course_id)
    if subject_id is not None:
        sessions = sessions.filter(models.LearningSession.subject_id == subject_id)
        assessments = assessments.filter(models.Assessment.subject_id == subject_id)
        questions = questions.filter(models.Question.subject_id == subject_id)
        remedial = remedial.filter(models.RemedialGroup.subject_id == subject_id)
        attempts = attempts.join(models.Assessment, models.Assessment.id == models.AssessmentAttempt.assessment_id).filter(models.Assessment.subject_id == subject_id)

    activity = {"students": db.query(models.StudentCourseEnrollment.id).filter(models.StudentCourseEnrollment.course_id == course_id).count(), "learning_sessions": sessions.count(), "completed_learning_sessions": sessions.filter(func.upper(models.LearningSession.status) == "COMPLETED").count(), "assessments": assessments.count(), "published_assessments": assessments.filter(func.upper(models.Assessment.status) == "PUBLISHED").count(), "assessment_attempts": attempts.count(), "average_percentage": attempts.with_entities(func.avg(models.AssessmentAttempt.percentage)).scalar(), "questions": questions.count(), "remedial_groups": remedial.count()}
    configured = {"subjects": sum(row.get("weight_percent") is not None for row in subjects), "units": sum(unit.get("weight_percent") is not None for row in subjects for unit in row.get("units", [])), "topics": sum(topic.get("weight_percent") is not None for row in subjects for unit in row.get("units", []) for topic in unit.get("topics", [])), "subtopics": sum(subtopic.get("weight_percent") is not None for row in subjects for unit in row.get("units", []) for topic in unit.get("topics", []) for subtopic in topic.get("subtopics", []))}
    total_items = len(subjects) + sum(len(row.get("units", [])) + sum(len(unit.get("topics", [])) + sum(len(topic.get("subtopics", [])) for topic in unit.get("topics", [])) for unit in row.get("units", [])) for row in subjects)
    complete_items = sum(configured.values())
    readiness = f"{round(complete_items / total_items * 100)}% configured" if total_items and complete_items else "Academic weightages not configured yet"
    course = scope["course"]
    return {"course": {"id": course.id, "title": course.title, "programme_code": course.programme_code, "programme_category": course.programme_category, "examination_name": course.examination_name, "examination_authority": course.examination_authority, "target_purpose": course.target_purpose, "description": course.description, "is_active": bool(course.is_active)}, "subject": subjects[0] if subject_id is not None else None, "subjects": subjects, "coordinators": coordinators, "experts": experts, "activity": activity, "configured": configured, "weightage_readiness": readiness, "syllabus_status": syllabus_status}


def _draft_subject_report_payload(db: Session, task: models.SyllabusSubjectReview, actor: models.User) -> dict:
    """Build a report projection for a saved syllabus subject awaiting publication."""
    from app.services.faculty_syllabus_scope import _tree
    from app.services.syllabus_subjects import branch

    review = db.get(models.SyllabusReview, task.review_id)
    if not review or task.reviewer_id != actor.id:
        raise HTTPException(status_code=403, detail="Subject expert responsibility is required")
    course = db.get(models.Course, review.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Assigned course not found")
    nodes = task.proposed_nodes or branch(review.proposed_nodes or [], task.subject_key)
    subjects = _tree(nodes, [task])
    if not subjects:
        raise HTTPException(status_code=404, detail="Assigned syllabus subject is unavailable")
    subject = subjects[0]
    live_subject_id = task.live_subject_id
    sessions = db.query(models.LearningSession).filter(models.LearningSession.course_id == course.id)
    assessments = db.query(models.Assessment).filter(models.Assessment.course_id == course.id)
    questions = db.query(models.Question).filter(models.Question.course_id == course.id)
    remedial = db.query(models.RemedialGroup).filter(models.RemedialGroup.course_id == course.id)
    attempts = db.query(models.AssessmentAttempt).filter(models.AssessmentAttempt.course_id == course.id)
    if live_subject_id:
        sessions = sessions.filter(models.LearningSession.subject_id == live_subject_id)
        assessments = assessments.filter(models.Assessment.subject_id == live_subject_id)
        questions = questions.filter(models.Question.subject_id == live_subject_id)
        remedial = remedial.filter(models.RemedialGroup.subject_id == live_subject_id)
        attempts = attempts.join(models.Assessment, models.Assessment.id == models.AssessmentAttempt.assessment_id).filter(models.Assessment.subject_id == live_subject_id)
    else:
        sessions = sessions.filter(models.LearningSession.id == -1)
        assessments = assessments.filter(models.Assessment.id == -1)
        questions = questions.filter(models.Question.id == -1)
        remedial = remedial.filter(models.RemedialGroup.id == -1)
        attempts = attempts.filter(models.AssessmentAttempt.id == -1)
    coordinators = [{"name": row.faculty.name, "employee_code": row.faculty.employee_code, "department": row.faculty.department, "designation": row.faculty.designation} for row in db.query(models.FacultyCourseAssignment).filter(models.FacultyCourseAssignment.course_id == course.id).all() if row.faculty]
    activity = {
        "students": db.query(models.StudentCourseEnrollment.id).filter(models.StudentCourseEnrollment.course_id == course.id, models.StudentCourseEnrollment.status.in_(("ACTIVE", "COMPLETED"))).count(),
        "learning_sessions": sessions.count(), "completed_learning_sessions": sessions.filter(func.upper(models.LearningSession.status) == "COMPLETED").count(),
        "assessments": assessments.count(), "published_assessments": assessments.filter(func.upper(models.Assessment.status) == "PUBLISHED").count(),
        "assessment_attempts": attempts.count(), "average_percentage": attempts.with_entities(func.avg(models.AssessmentAttempt.percentage)).scalar(),
        "questions": questions.count(), "remedial_groups": remedial.count(),
    }
    configured = {
        "subjects": sum(item.get("weight_percent") is not None for item in subjects),
        "units": sum(unit.get("weight_percent") is not None for item in subjects for unit in item.get("units", [])),
        "topics": sum(topic.get("weight_percent") is not None for item in subjects for unit in item.get("units", []) for topic in unit.get("topics", [])),
        "subtopics": sum(subtopic.get("weight_percent") is not None for item in subjects for unit in item.get("units", []) for topic in unit.get("topics", []) for subtopic in topic.get("subtopics", [])),
    }
    return {
        "course": {"id": course.id, "title": course.title, "programme_code": course.programme_code, "programme_category": course.programme_category, "examination_name": course.examination_name, "examination_authority": course.examination_authority, "target_purpose": course.target_purpose, "description": course.description, "is_active": bool(course.is_active)},
        "subject": subject, "subjects": subjects, "coordinators": coordinators,
        "experts": [{"name": actor.name, "employee_code": actor.employee_code, "department": actor.department, "designation": actor.designation, "subject_name": subject["name"], "subject_id": live_subject_id}],
        "activity": activity, "configured": configured,
        "weightage_readiness": "Academic weightages not configured yet" if not sum(configured.values()) else "Partially configured",
        "syllabus_status": f"Saved syllabus review assignment - {str(task.status or 'ASSIGNED').replace('_', ' ').title()}",
        "assignment": {"review_id": task.review_id, "review_task_id": task.id, "subject_key": task.subject_key, "review_status": task.status, "live_subject_id": live_subject_id},
    }


def _course_enrolled_students(db: Session, course_id: int) -> list[dict]:
    rows = db.query(models.StudentCourseEnrollment).filter(models.StudentCourseEnrollment.course_id == course_id, models.StudentCourseEnrollment.status.in_(("ACTIVE", "COMPLETED"))).order_by(models.StudentCourseEnrollment.student_id).all()
    return [{"id": row.student_id, "name": row.student.name, "roll_number": row.student.roll_number, "academic_program": row.student.academic_program, "present_year": row.student.present_year, "college": row.student.college, "status": row.status} for row in rows if row.student]


def _course_report_response(db: Session, course_id: int, actor: models.User, report_type: str, subject_id: int | None = None) -> Response:
    payload = _course_report_payload(db, course_id, actor, subject_id)
    content = build_course_profile_pdf(payload, generated_by=actor.name or actor.email or "SYS academic user", report_type=report_type)
    name = payload["subject"]["name"] if payload.get("subject") else payload["course"].get("programme_code") or payload["course"]["title"]
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(name)).strip("_") or str(course_id)
    scope_name = "Subject" if subject_id is not None else "Course"
    report_name = "Syllabus_Weightages" if report_type == "syllabus" else "Profile"
    stamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    management_service.record_audit(db, actor, action=f"{scope_name.lower()}.report.download", target_type="subject" if subject_id is not None else "course", target_id=subject_id or course_id, summary=f"Downloaded {scope_name.lower()} {report_type} report: {name}", changed_fields=[])
    db.commit()
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="SYS_{scope_name}_{report_name}_{safe}_{stamp}.pdf"'})


@router.get("/courses/{course_id}/profile.pdf")
def download_course_profile_pdf(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    return _course_report_response(db, course_id, actor, "profile")


@router.get("/course-coordinators/my-courses.pdf")
def download_my_coordinator_courses_pdf(db: Session = Depends(database.get_db), actor: models.User = Depends(_faculty)):
    assignments = db.query(models.FacultyCourseAssignment).filter(models.FacultyCourseAssignment.faculty_id == actor.id).order_by(models.FacultyCourseAssignment.course_id).all()
    payloads = [_course_report_payload(db, row.course_id, actor) for row in assignments]
    content = build_coordinator_courses_pdf(payloads, generated_by=actor.name or actor.email or "SYS course coordinator")
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(actor.employee_code or actor.name or actor.id)).strip("_") or str(actor.id)
    stamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    management_service.record_audit(db, actor, action="course_coordinator.portfolio.download", target_type="faculty", target_id=actor.id, summary=f"Downloaded coordinator portfolio for {len(payloads)} assigned courses", changed_fields=[])
    db.commit()
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="SYS_Coordinator_Assigned_Courses_{safe}_{stamp}.pdf"'})


@router.get("/subject-experts/my-subjects.pdf")
def download_my_subject_expert_assignments_pdf(db: Session = Depends(database.get_db), actor: models.User = Depends(_faculty)):
    from app.services.faculty_syllabus_scope import faculty_draft_assignments

    assignments = db.query(models.SubjectExpertAssignment).join(models.Subject, models.Subject.id == models.SubjectExpertAssignment.subject_id).filter(models.SubjectExpertAssignment.faculty_id == actor.id).order_by(models.Subject.course_id, models.SubjectExpertAssignment.subject_id).all()
    payloads = [_course_report_payload(db, row.subject.course_id, actor, row.subject_id) for row in assignments if row.subject]
    for assignment in faculty_draft_assignments(db, actor.id):
        task = db.get(models.SyllabusSubjectReview, assignment["review_task_id"])
        if task:
            payloads.append(_draft_subject_report_payload(db, task, actor))
    content = build_subject_expert_assignments_pdf(payloads, generated_by=actor.name or actor.email or "SYS subject expert")
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(actor.employee_code or actor.name or actor.id)).strip("_") or str(actor.id)
    stamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    management_service.record_audit(db, actor, action="subject_expert.portfolio.download", target_type="faculty", target_id=actor.id, summary=f"Downloaded subject-expert portfolio for {len(payloads)} assigned subjects", changed_fields=[])
    db.commit()
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="SYS_Subject_Expert_Assignments_{safe}_{stamp}.pdf"'})


def _subject_expert_information_payload(db: Session, actor: models.User, course_id: int, subject_id: int | None, review_task_id: int | None) -> dict:
    if (subject_id is None) == (review_task_id is None):
        raise HTTPException(status_code=422, detail="Provide exactly one subject assignment reference")
    if subject_id is not None:
        assignment = db.query(models.SubjectExpertAssignment).join(models.Subject).filter(models.SubjectExpertAssignment.faculty_id == actor.id, models.SubjectExpertAssignment.subject_id == subject_id, models.Subject.course_id == course_id).first()
        if not assignment:
            raise HTTPException(status_code=403, detail="Subject expert responsibility is required")
        payload = _course_report_payload(db, course_id, actor, subject_id)
        payload["assignment"] = {"subject_id": subject_id, "review_status": "ASSIGNED"}
    else:
        task = db.query(models.SyllabusSubjectReview).join(models.SyllabusReview, models.SyllabusReview.id == models.SyllabusSubjectReview.review_id).filter(models.SyllabusSubjectReview.id == review_task_id, models.SyllabusSubjectReview.reviewer_id == actor.id, models.SyllabusReview.course_id == course_id).first()
        if not task:
            raise HTTPException(status_code=403, detail="Subject expert responsibility is required")
        payload = _draft_subject_report_payload(db, task, actor)
    payload["enrolled_students"] = _course_enrolled_students(db, course_id)
    payload["enrollment_scope"] = "Course-level enrollment; SYS does not assign students separately to individual subjects."
    return payload


@router.get("/subject-experts/subject-information")
def subject_expert_information(course_id: int, subject_id: int | None = None, review_task_id: int | None = None, db: Session = Depends(database.get_db), actor: models.User = Depends(_faculty)):
    return _subject_expert_information_payload(db, actor, course_id, subject_id, review_task_id)


@router.get("/subject-experts/subject-information.pdf")
def download_subject_expert_information_pdf(course_id: int, subject_id: int | None = None, review_task_id: int | None = None, db: Session = Depends(database.get_db), actor: models.User = Depends(_faculty)):
    payload = _subject_expert_information_payload(db, actor, course_id, subject_id, review_task_id)
    content = build_course_profile_pdf(payload, generated_by=actor.name or actor.email or "SYS subject expert", report_type="profile")
    subject = payload["subject"]
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", str(subject.get("name") or "Subject")).strip("_") or "Subject"
    stamp = datetime.now(timezone(timedelta(hours=5, minutes=30))).strftime("%Y-%m-%d")
    management_service.record_audit(db, actor, action="subject_expert.information.download", target_type="subject", target_id=subject_id, summary=f"Downloaded assigned subject information: {subject.get('name')}", changed_fields=[])
    db.commit()
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="SYS_Subject_Information_{safe}_{stamp}.pdf"'})


@router.get("/courses/{course_id}/syllabus.pdf")
def download_course_syllabus_pdf(course_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    from app.routes.syllabus_review import approved_pdf
    return approved_pdf(course_id, revision=None, subject_id=None, db=db, actor=actor)


@router.get("/courses/{course_id}/subjects/{subject_id}/profile.pdf")
def download_subject_profile_pdf(course_id: int, subject_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    return _course_report_response(db, course_id, actor, "profile", subject_id)


@router.get("/courses/{course_id}/subjects/{subject_id}/syllabus.pdf")
def download_subject_syllabus_pdf(course_id: int, subject_id: int, db: Session = Depends(database.get_db), actor: models.User = Depends(_academic_staff)):
    from app.routes.syllabus_review import approved_pdf
    return approved_pdf(course_id, revision=None, subject_id=subject_id, db=db, actor=actor)


# =========================
# Course Coordinator (uses FacultyCourseAssignment)
# =========================
@router.get("/course-coordinators", response_model=List[schemas.CourseCoordinatorOut])
def list_course_coordinators(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    rows = db.query(models.FacultyCourseAssignment).all()
    return [_coordinator_out(r) for r in rows]


@router.post(
    "/course-coordinators",
    response_model=schemas.CourseCoordinatorOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_course_coordinator(
    payload: schemas.CourseCoordinatorCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    faculty = _get_role_user(db, payload.faculty_id, "faculty")
    if not faculty.is_active:
        raise HTTPException(status_code=400, detail="Faculty account is inactive")
    course = db.query(models.Course).filter(models.Course.id == payload.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    existing = (
        db.query(models.FacultyCourseAssignment)
        .filter(
            models.FacultyCourseAssignment.faculty_id == payload.faculty_id,
            models.FacultyCourseAssignment.course_id == payload.course_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Course Coordinator assignment already exists")
    row = models.FacultyCourseAssignment(
        faculty_id=payload.faculty_id,
        course_id=payload.course_id,
    )
    db.add(row)
    try:
        db.flush()
        management_service.record_audit(db, current_admin, action="faculty.assign_course_coordinator", target_type="faculty", target_id=faculty.id, summary=f"Assigned {faculty.name} as course coordinator for {course.title}", changed_fields=["course_coordinator_assignment"])
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Course Coordinator assignment already exists")
    db.refresh(row)
    # ensure relationships loaded
    db.refresh(row)
    row = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.id == row.id)
        .first()
    )
    return _coordinator_out(row)


@router.delete("/course-coordinators/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_course_coordinator(
    assignment_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    row = (
        db.query(models.FacultyCourseAssignment)
        .filter(models.FacultyCourseAssignment.id == assignment_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    management_service.record_audit(db, current_admin, action="faculty.remove_course_coordinator", target_type="faculty", target_id=row.faculty_id, summary=f"Removed course coordinator assignment for {row.course.title if row.course else row.course_id}", changed_fields=["course_coordinator_assignment"])
    db.delete(row)
    db.commit()
    return None


# =========================
# Subject Expert
# =========================
@router.get("/subject-experts", response_model=List[schemas.SubjectExpertOut])
def list_subject_experts(
    db: Session = Depends(database.get_db),
    _: models.User = Depends(_admin),
):
    rows = db.query(models.SubjectExpertAssignment).all()
    return [_expert_out(r) for r in rows]


@router.post(
    "/subject-experts",
    response_model=schemas.SubjectExpertOut,
    status_code=status.HTTP_201_CREATED,
)
def assign_subject_expert(
    payload: schemas.SubjectExpertCreate,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    faculty = _get_role_user(db, payload.faculty_id, "faculty")
    if not faculty.is_active:
        raise HTTPException(status_code=400, detail="Faculty account is inactive")
    subject = db.query(models.Subject).filter(models.Subject.id == payload.subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    existing = (
        db.query(models.SubjectExpertAssignment)
        .filter(
            models.SubjectExpertAssignment.faculty_id == payload.faculty_id,
            models.SubjectExpertAssignment.subject_id == payload.subject_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Subject Expert assignment already exists")
    row = models.SubjectExpertAssignment(
        faculty_id=payload.faculty_id,
        subject_id=payload.subject_id,
    )
    db.add(row)
    try:
        db.flush()
        management_service.record_audit(db, current_admin, action="faculty.assign_subject_expert", target_type="faculty", target_id=faculty.id, summary=f"Assigned {faculty.name} as subject expert for {subject.name}", changed_fields=["subject_expert_assignment"])
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Subject Expert assignment already exists")
    db.refresh(row)
    row = (
        db.query(models.SubjectExpertAssignment)
        .filter(models.SubjectExpertAssignment.id == row.id)
        .first()
    )
    return _expert_out(row)


@router.delete("/subject-experts/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_subject_expert(
    assignment_id: int,
    db: Session = Depends(database.get_db),
    current_admin: models.User = Depends(_admin),
):
    row = (
        db.query(models.SubjectExpertAssignment)
        .filter(models.SubjectExpertAssignment.id == assignment_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    management_service.record_audit(db, current_admin, action="faculty.remove_subject_expert", target_type="faculty", target_id=row.faculty_id, summary=f"Removed subject expert assignment for {row.subject.name if row.subject else row.subject_id}", changed_fields=["subject_expert_assignment"])
    db.delete(row)
    db.commit()
    return None
