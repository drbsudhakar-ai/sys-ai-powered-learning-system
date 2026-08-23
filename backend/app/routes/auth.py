"""Unified authentication, controlled activation, and OTP recovery routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import database, models, roles, schemas
from app.services import authentication as auth_service
from app.services.otp_delivery import OtpDeliveryProvider, get_otp_provider  # ✅ ensure OTP imports
import app.utils as utils  # ✅ import whole utils module

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

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

# ✅ Keep your activation and password reset routes as they are, now with proper OTP imports
@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
