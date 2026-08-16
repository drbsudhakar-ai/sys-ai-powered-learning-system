"""Unified authentication, controlled activation, and OTP recovery routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import database, models, schemas, utils
from app.services import authentication as auth_service
from app.services.otp_delivery import OtpDeliveryProvider, get_otp_provider


router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


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
    access_token = utils.create_access_token(
        data={"sub": str(user.id), "sv": int(user.session_version or 1)}
    )
    return {"access_token": access_token, "token_type": "bearer"}


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


def require_roles(*allowed_roles: str):
    """Require an active authenticated user whose role is allowed."""

    allowed = {role.lower() for role in allowed_roles}

    def _checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if (current_user.role or "").lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def provision_legacy(
    payload: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """Backward-compatible administrator-only provisioning endpoint."""

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
        request_ip=request.client.host if request.client else None,
        provider=provider,
    )
    return {
        "challenge_id": challenge.id,
        "message": auth_service.GENERIC_ACTIVATION_ERROR,
    }


@router.post("/activation/verify-otp", response_model=schemas.AuthorizationResponse)
def activation_verify_otp(
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
def activation_verify_contact(
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
            request_ip=request.client.host if request.client else None,
            provider=provider,
        )
        return {"challenge_id": challenge.id, "message": "Verification code requested."}

    if not payload.challenge_id or not payload.code:
        raise HTTPException(status_code=422, detail="Challenge and verification code are required")
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
    return {"message": "Registration complete. Log in to continue."}


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
        request_ip=request.client.host if request.client else None,
        provider=provider,
    )
    return {"challenge_id": challenge.id, "message": auth_service.GENERIC_RECOVERY_MESSAGE}


@router.post("/password-reset/verify-otp", response_model=schemas.AuthorizationResponse)
def password_reset_verify_otp(
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
    return {"message": "Password updated. Log in with your new password."}


@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
