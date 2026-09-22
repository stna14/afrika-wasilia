import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.auth import PASSWORD_MIN_LENGTH, _validate_password_strength


class AdminCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=20)
    password: str
    role_id: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        return _validate_password_strength(v)


class AdminUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    profile_image: str | None = Field(default=None, max_length=255)


class AdminRoleUpdate(BaseModel):
    role_id: str


class AdminStatusUpdate(BaseModel):
    account_status: str = Field(pattern="^(active|suspended|disabled)$")


class AdminDetail(BaseModel):
    admin_id: str
    full_name: str
    email: str
    phone: str | None
    role_id: str
    role_name: str
    account_status: str
    two_factor_enabled: bool
    profile_image: str | None
    last_login: str | None
    created_by: str | None

    model_config = {"from_attributes": True}