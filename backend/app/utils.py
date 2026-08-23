from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from app.config import settings

# =========================
# Password Hashing
# =========================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt (truncate to 72 bytes)."""
    password = password[:72]  # bcrypt limit
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against its hash (truncate to 72 bytes)."""
    if not is_usable_password_hash(hashed_password):
        return False
    plain_password = plain_password[:72]  # bcrypt limit
    return pwd_context.verify(plain_password, hashed_password)

def is_usable_password_hash(hashed_password: str | None) -> bool:
    return bool(hashed_password and pwd_context.identify(hashed_password))

def validate_password(password: str, confirmation: str | None = None) -> None:
    """Validate a password without returning or logging the secret value."""
    if confirmation is not None and password != confirmation:
        raise ValueError("Passwords do not match")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password cannot exceed 72 bytes (bcrypt limit)")

# =========================
# JWT Token Management
# =========================
ACCESS_TOKEN_EXPIRE_MINUTES = 30
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
