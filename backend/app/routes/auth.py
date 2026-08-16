"""
Authentication Routes
---------------------
SYS AI Lecturer System
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import models, schemas, database, utils

router = APIRouter(prefix="/auth", tags=["Authentication"])
MIN_PROVISIONED_PASSWORD_LENGTH = 8
MAX_BCRYPT_PASSWORD_BYTES = 72

# OAuth2 scheme for JWT bearer tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# =========================
# Login User
# =========================
@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.is_active is False:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access_token = utils.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}


# =========================
# Get Current User
# =========================
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(database.get_db)):
    payload = utils.decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    try:
        user_pk = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = db.query(models.User).filter(models.User.id == user_pk).first()
    if user is None or user.is_active is False:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def require_roles(*allowed_roles: str):
    """Dependency factory: require an authenticated user whose role is allowed."""

    allowed = {role.lower() for role in allowed_roles}

    def _checker(current_user: models.User = Depends(get_current_user)) -> models.User:
        if (current_user.role or "").lower() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _checker


# =========================
# Administrator Provisioning
# =========================
@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(
    user: schemas.UserCreate,
    db: Session = Depends(database.get_db),
    _: models.User = Depends(require_roles("admin")),
):
    """Provision a student or faculty account from an authenticated admin session."""

    if user.role == "student" and not user.roll_number:
        raise HTTPException(status_code=422, detail="Institutional identifier is required")
    if user.role == "faculty" and not user.employee_code:
        raise HTTPException(status_code=422, detail="Institutional identifier is required")

    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    password = user.password.get_secret_value()
    if len(password) < MIN_PROVISIONED_PASSWORD_LENGTH or len(password.encode("utf-8")) > MAX_BCRYPT_PASSWORD_BYTES:
        raise HTTPException(status_code=422, detail="Password does not meet security requirements")

    new_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=utils.hash_password(password),
        role=user.role,
        roll_number=user.roll_number,
        employee_code=user.employee_code,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


# =========================
# Protected Route Example
# =========================
@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    return current_user
