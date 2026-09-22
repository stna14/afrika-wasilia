import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ---- Password hashing ----
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.BCRYPT_ROUNDS,
)


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


# ---- Token hashing (refresh tokens, reset tokens) ----
def hash_token(raw_token: str) -> str:
    """SHA-256 hash a token for storage. Deterministic, fast, one-way."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_token(nbytes: int = 32) -> str:
    """Cryptographically secure random token (URL-safe)."""
    return secrets.token_urlsafe(nbytes)


# ---- JWT ----
def create_access_token(
    subject: str,
    extra: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Issue a short-lived JWT access token."""
    minutes = expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str) -> str:
    """Issue a long-lived JWT refresh token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(
            (now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)).timestamp()
        ),
        "type": "refresh",
        "jti": generate_token(16),  # unique per token
    }
    return jwt.encode(
        payload, settings.JWT_REFRESH_SECRET, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode + validate an access token. Raises JWTError if invalid."""
    return jwt.decode(
        token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Decode + validate a refresh token. Raises JWTError if invalid."""
    return jwt.decode(
        token, settings.JWT_REFRESH_SECRET, algorithms=[settings.JWT_ALGORITHM]
    )