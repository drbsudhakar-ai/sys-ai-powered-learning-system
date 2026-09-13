"""Unified authentication, controlled activation, and OTP recovery routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from pathlib import Path
import re
import uuid

from app import database, models, roles, schemas
from app.services import authentication as auth_service
from app.services.otp_delivery import OtpDeliveryProvider, get_otp_provider  # ✅ ensure OTP imports
import app.utils as utils  # ✅ import whole utils module

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

PROFILE_PHOTO_MAX_BYTES = 5 * 1024 * 1024
PROFILE_PHOTO_DIRECTORY = Path(__file__).resolve().parents[3] / "frontend" / "public" / "photos"
PROFILE_PHOTO_TYPES = {
    "image/jpeg": (".jpg", (b"\xff\xd8\xff",)),
    "image/png": (".png", (b"\x89PNG\r\n\x1a\n",)),
    "image/webp": (".webp", (b"RIFF",)),
}

# =========================
# Login Route
# =========================
@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(database.get_db),
):
    user = auth_service.authenticate_identifier(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=auth_service.GENERIC_LOGIN_ERROR,
        )

    access_token = utils.create_access_token(data={"sub": str(user.id), "sv": str(user.session_version or 1)})
    return {"access_token": access_token, "token_type": "bearer"}

# =========================
# Current User
# =========================
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(database.get_db),
):
    payload = utils.decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        user_pk = int(payload.get("sub"))
        token_session_version = int(payload.get("sv"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == user_pk).first()
    if (
        not auth_service.account_can_authenticate(user)
        or token_session_version != int(user.session_version or 1)
    ):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user

# =========================
# Role Requirements
# =========================
def require_roles(*allowed_roles: str):
    allowed = {role.lower() for role in allowed_roles}
    def _checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if not roles.grants_any_role(current_user.role, allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return _checker

def require_super_admin(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    if not roles.is_super_admin_role(current_user.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super Admin permissions required",
        )
    return current_user


@router.post(
    "/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
)
def register_provisioned_user(
    payload: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(require_roles(roles.ADMIN)),
):
    """Preserve the administrator-only immediate account provisioning API."""

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


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/activation/start", response_model=schemas.ChallengeStartResponse)
def activation_start(
    payload: schemas.ActivationStartRequest,
    request: Request,
    db: Session = Depends(database.get_db),
    provider: OtpDeliveryProvider = Depends(get_otp_provider),
):
    challenge = auth_service.start_activation(
        db,
        role=payload.role,
        institutional_id=payload.institutional_id,
        channel=payload.channel,
        request_ip=_request_ip(request),
        provider=provider,
    )
    return {
        "challenge_id": challenge.id,
        "message": auth_service.GENERIC_ACTIVATION_ERROR,
        "identity": auth_service.activation_identity_summary(
            db.query(models.User).filter(models.User.id == challenge.user_id).first()
            if challenge.user_id
            else None
        ),
    }


@router.post("/activation/verify-otp", response_model=schemas.AuthorizationResponse)
def activation_verify_ownership(
    payload: schemas.OtpVerifyRequest,
    db: Session = Depends(database.get_db),
):
    _, authorization = auth_service.verify_otp_challenge(
        db,
        challenge_id=payload.challenge_id,
        code=payload.code,
        allowed_purposes={auth_service.PURPOSE_ACTIVATION_OWNERSHIP},
    )
    return {"authorization": authorization}


@router.post("/activation/verify-contact")
def activation_contact(
    payload: schemas.ActivationContactRequest,
    request: Request,
    db: Session = Depends(database.get_db),
    provider: OtpDeliveryProvider = Depends(get_otp_provider),
):
    if payload.action == "send":
        if not payload.contact_value:
            raise HTTPException(status_code=422, detail="Contact value is required")
        challenge = auth_service.start_activation_contact(
            db,
            ownership_authorization=payload.ownership_authorization,
            contact_type=payload.contact_type,
            contact_value=payload.contact_value,
            request_ip=_request_ip(request),
            provider=provider,
        )
        return {
            "challenge_id": challenge.id,
            "message": "A verification code has been requested.",
        }

    if not payload.challenge_id or not payload.code:
        raise HTTPException(
            status_code=422,
            detail="Challenge ID and verification code are required",
        )
    authorization = auth_service.verify_activation_contact(
        db,
        ownership_authorization=payload.ownership_authorization,
        contact_type=payload.contact_type,
        challenge_id=payload.challenge_id,
        code=payload.code,
    )
    return {"authorization": authorization}


@router.post("/activation/complete", response_model=schemas.AuthMessageResponse)
def activation_complete(
    payload: schemas.ActivationCompleteRequest,
    db: Session = Depends(database.get_db),
):
    auth_service.complete_activation(
        db,
        ownership_authorization=payload.ownership_authorization,
        email=str(payload.email),
        email_authorization=payload.email_authorization,
        mobile_number=payload.mobile_number,
        mobile_authorization=payload.mobile_authorization,
        password=payload.password.get_secret_value(),
        confirm_password=payload.confirm_password.get_secret_value(),
    )
    return {"message": "Registration completed successfully."}


@router.post("/password-reset/start", response_model=schemas.ChallengeStartResponse)
def password_reset_start(
    payload: schemas.PasswordResetStartRequest,
    request: Request,
    db: Session = Depends(database.get_db),
    provider: OtpDeliveryProvider = Depends(get_otp_provider),
):
    challenge = auth_service.start_password_reset(
        db,
        identifier=payload.identifier,
        channel=payload.channel,
        request_ip=_request_ip(request),
        provider=provider,
    )
    return {
        "challenge_id": challenge.id,
        "message": auth_service.GENERIC_RECOVERY_MESSAGE,
    }


@router.post("/password-reset/verify-otp", response_model=schemas.AuthorizationResponse)
def password_reset_verify(
    payload: schemas.OtpVerifyRequest,
    db: Session = Depends(database.get_db),
):
    _, authorization = auth_service.verify_otp_challenge(
        db,
        challenge_id=payload.challenge_id,
        code=payload.code,
        allowed_purposes={
            auth_service.PURPOSE_PASSWORD_RESET_EMAIL,
            auth_service.PURPOSE_PASSWORD_RESET_MOBILE,
        },
    )
    return {"authorization": authorization}


@router.post("/password-reset/complete", response_model=schemas.AuthMessageResponse)
def password_reset_complete(
    payload: schemas.PasswordResetCompleteRequest,
    db: Session = Depends(database.get_db),
    provider: OtpDeliveryProvider = Depends(get_otp_provider),
):
    auth_service.complete_password_reset(
        db,
        reset_authorization=payload.reset_authorization,
        password=payload.password.get_secret_value(),
        confirm_password=payload.confirm_password.get_secret_value(),
        provider=provider,
    )
    return {"message": "Password updated successfully."}


@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return _self_profile_out(current_user)


def _existing_self_profile_photo(user: models.User) -> str | None:
    """Resolve database-managed and legacy convention-based photographs."""
    if user.photo_url:
        return user.photo_url
    identifier = user.roll_number if roles.normalize_role(user.role) == roles.STUDENT else user.employee_code
    if not identifier or not PROFILE_PHOTO_DIRECTORY.is_dir():
        return None
    expected = {
        str(identifier).lower(),
        f"{roles.normalize_role(user.role)}-{identifier}".lower(),
        f"{roles.normalize_role(user.role)}-{user.id}".lower(),
    }
    matches = [
        path for path in PROFILE_PHOTO_DIRECTORY.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        and (path.stem.lower() in expected or any(path.stem.lower().startswith(f"{stem}-") for stem in expected))
    ]
    if not matches:
        return None
    selected = max(matches, key=lambda path: path.stat().st_mtime)
    return f"/photos/{selected.name}"


def _self_profile_out(user: models.User) -> schemas.UserOut:
    return schemas.UserOut.model_validate(user).model_copy(
        update={"photo_url": _existing_self_profile_photo(user)}
    )


def _require_self_service_role(user: models.User) -> None:
    if roles.normalize_role(user.role) not in {roles.STUDENT, roles.FACULTY}:
        raise HTTPException(status_code=403, detail="Self-service profiles are available to students and faculty")


def _managed_profile_photo(photo_url: str | None) -> Path | None:
    if not photo_url or not photo_url.startswith("/photos/"):
        return None
    filename = Path(photo_url).name
    if not re.fullmatch(r"(?:student|faculty)-\d+-[a-f0-9]{12}\.(?:jpg|png|webp)", filename):
        return None
    candidate = (PROFILE_PHOTO_DIRECTORY / filename).resolve()
    return candidate if candidate.parent == PROFILE_PHOTO_DIRECTORY.resolve() else None


async def _save_self_profile_photo(photo: UploadFile, user: models.User) -> tuple[str, Path]:
    content_type = (photo.content_type or "").lower()
    definition = PROFILE_PHOTO_TYPES.get(content_type)
    if not definition:
        raise HTTPException(status_code=422, detail="Profile photo must be JPEG, PNG or WebP")
    content = await photo.read(PROFILE_PHOTO_MAX_BYTES + 1)
    await photo.close()
    if not content:
        raise HTTPException(status_code=422, detail="Profile photo is empty")
    if len(content) > PROFILE_PHOTO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Profile photo must not exceed 5 MB")
    extension, signatures = definition
    valid = any(content.startswith(signature) for signature in signatures)
    if content_type == "image/webp":
        valid = valid and len(content) >= 12 and content[8:12] == b"WEBP"
    if not valid:
        raise HTTPException(status_code=422, detail="Profile photo content does not match its file type")
    PROFILE_PHOTO_DIRECTORY.mkdir(parents=True, exist_ok=True)
    filename = f"{roles.normalize_role(user.role)}-{user.id}-{uuid.uuid4().hex[:12]}{extension}"
    path = PROFILE_PHOTO_DIRECTORY / filename
    path.write_bytes(content)
    return f"/photos/{filename}", path


@router.patch("/me/profile", response_model=schemas.UserOut)
def update_my_profile(
    payload: schemas.SelfProfileUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    _require_self_service_role(current_user)
    if "mobile_number" in payload.model_fields_set:
        if payload.mobile_number:
            try:
                mobile = auth_service.normalize_mobile(payload.mobile_number)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            duplicate = (
                db.query(models.User.id)
                .filter(models.User.id != current_user.id, func.lower(models.User.mobile_number) == mobile.lower())
                .first()
            )
            if duplicate:
                raise HTTPException(status_code=409, detail="Mobile number is already used by another SYS account")
        else:
            mobile = None
        if mobile != current_user.mobile_number:
            current_user.mobile_number = mobile
            current_user.mobile_verified = False
            current_user.mobile_is_personal = True
    db.commit()
    db.refresh(current_user)
    return _self_profile_out(current_user)


@router.post("/me/photo", response_model=schemas.UserOut)
async def upload_my_profile_photo(
    photo: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    _require_self_service_role(current_user)
    previous = _managed_profile_photo(current_user.photo_url)
    photo_url, written = await _save_self_profile_photo(photo, current_user)
    try:
        current_user.photo_url = photo_url
        db.commit()
        db.refresh(current_user)
    except Exception:
        db.rollback()
        written.unlink(missing_ok=True)
        raise
    if previous and previous != written:
        previous.unlink(missing_ok=True)
    return _self_profile_out(current_user)


@router.delete("/me/photo", response_model=schemas.UserOut)
def remove_my_profile_photo(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    _require_self_service_role(current_user)
    previous = _managed_profile_photo(current_user.photo_url)
    current_user.photo_url = None
    db.commit()
    db.refresh(current_user)
    if previous:
        previous.unlink(missing_ok=True)
    return _self_profile_out(current_user)


@router.get("/dashboard")
def role_dashboard(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(database.get_db),
):
    role = roles.normalize_role(current_user.role)

    if role == roles.STUDENT:
        enrollments = (
            db.query(models.StudentCourseEnrollment)
            .filter(models.StudentCourseEnrollment.student_id == current_user.id, models.StudentCourseEnrollment.status == "ACTIVE")
            .all()
        )
        courses = [
            {
                "id": enrollment.course.id,
                "title": enrollment.course.title,
                "programme_code": enrollment.course.programme_code,
                "enrolled_at": enrollment.enrolled_at,
            }
            for enrollment in enrollments
            if enrollment.course
            and enrollment.course.is_active
            and str(getattr(enrollment.course, "publication_status", "PUBLISHED"))
            .upper()
            .split(".")[-1]
            in {"PUBLISHED", "PILOT_PUBLISHED"}
        ]
        return {
            "role": role,
            "identity": {
                "name": current_user.name,
                "roll_number": current_user.roll_number,
                "college": current_user.college,
                "academic_program": current_user.academic_program,
                "photo_url": _existing_self_profile_photo(current_user),
            },
            "summary": {
                "enrolled_courses": len(courses),
                "learning_status": "NOT_STARTED",
                "upcoming_assessments": 0,
                "attention_required": 0,
            },
            "courses": courses,
        }

    if role == roles.FACULTY:
        from app.services.faculty_syllabus_scope import faculty_draft_assignments

        coordinators = (
            db.query(models.FacultyCourseAssignment)
            .filter(models.FacultyCourseAssignment.faculty_id == current_user.id)
            .all()
        )
        experts = (
            db.query(models.SubjectExpertAssignment)
            .filter(models.SubjectExpertAssignment.faculty_id == current_user.id)
            .all()
        )
        draft_subjects = faculty_draft_assignments(db, current_user.id)
        course_ids = {assignment.course_id for assignment in coordinators} | {
            assignment.subject.course_id
            for assignment in experts
            if assignment.subject and assignment.subject.course_id is not None
        } | {assignment["course_id"] for assignment in draft_subjects}
        students = (
            db.query(models.StudentCourseEnrollment.student_id)
            .filter(models.StudentCourseEnrollment.course_id.in_(course_ids))
            .distinct()
            .count()
            if course_ids
            else 0
        )
        return {
            "role": role,
            "identity": {
                "name": current_user.name,
                "employee_code": current_user.employee_code,
                "college": current_user.college,
                "department": current_user.department,
                "designation": current_user.designation,
                "photo_url": _existing_self_profile_photo(current_user),
            },
            "summary": {
                "assigned_courses": len(course_ids),
                "assigned_subjects": len({f"live:{assignment.subject_id}" for assignment in experts} | {f"draft:{assignment['course_id']}:{assignment['subject_key']}" for assignment in draft_subjects}),
                "enrolled_students": students,
                "attention_required": 0,
            },
            "courses": [
                {
                    "id": assignment.course.id,
                    "title": assignment.course.title,
                    "programme_code": assignment.course.programme_code,
                    "responsibility": "COURSE_COORDINATOR",
                }
                for assignment in coordinators
                if assignment.course
            ],
            "subjects": [
                {
                    "id": assignment.subject.id,
                    "name": assignment.subject.name,
                    "course_id": assignment.subject.course_id,
                    "course_title": (
                        assignment.subject.course.title
                        if assignment.subject.course
                        else None
                    ),
                    "responsibility": "SUBJECT_EXPERT",
                }
                for assignment in experts
                if assignment.subject
            ] + draft_subjects,
        }

    if roles.is_admin_role(role):
        return {
            "role": role,
            "identity": {"name": current_user.name},
            "summary": {},
        }

    raise HTTPException(
        status_code=403,
        detail="Dashboard access is not available for this role",
    )
