"""
Security utilities — password hashing and JWT token management.
"""
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return bcrypt hash of the plain password."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Password policy validation
# ---------------------------------------------------------------------------
def validate_password_strength(password: str) -> list[str]:
    """
    Validate password against system policy.
    Returns a list of violated rules (empty list = password is valid).
    """
    errors: list[str] = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long.")

    if settings.PASSWORD_REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter.")

    if settings.PASSWORD_REQUIRE_DIGIT and not re.search(r"\d", password):
        errors.append("Password must contain at least one digit.")

    if settings.PASSWORD_REQUIRE_SPECIAL and not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        errors.append("Password must contain at least one special character.")

    return errors


def generate_temp_password(length: int = 12) -> str:
    """Generate a cryptographically secure temporary password that satisfies policy."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if not validate_password_strength(pwd):
            return pwd


# ---------------------------------------------------------------------------
# JWT token creation
# ---------------------------------------------------------------------------
_UTC = timezone.utc


def _utcnow() -> datetime:
    return datetime.now(_UTC)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a short-lived JWT access token."""
    to_encode = data.copy()
    expire = _utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a long-lived JWT refresh token."""
    to_encode = data.copy()
    expire = _utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT.
    Raises JWTError if invalid or expired.
    """
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
