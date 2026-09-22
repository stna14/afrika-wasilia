import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---- Password policy ----
PASSWORD_MIN_LENGTH = 10


def _validate_password_strength(v: str) -> str:
    """Enforce password policy: 10+ chars, mixed case, number, symbol."""
    if len(v) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Z]", v):
        raise ValueError("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", v):
        raise ValueError("Password must contain a lowercase letter")
    if not re.search(r"\d", v):
        raise ValueError("Password must contain a number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]~`]", v):
        raise ValueError("Password must contain a special character")
    return v


# ---- Requests ----
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)  # don't reveal policy on login


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=10)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


# ---- Responses ----
class AdminSummary(BaseModel):
    admin_id: str
    full_name: str
    email: str
    role_name: str
    account_status: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int          # seconds until access token expires
    admin: AdminSummary


class MessageResponse(BaseModel):
    message: str


class SessionInfo(BaseModel):
    session_id: str
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}