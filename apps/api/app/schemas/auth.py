import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, validator


ACCOUNT_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,79}$")


class RegisterRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=8, max_length=128)
    invite_code: str = Field(min_length=1, max_length=80)

    @validator("email")
    @classmethod
    def validate_email(cls, email: str) -> str:
        normalized = email.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("valid email is required")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(max_length=320)
    password: str = Field(min_length=1, max_length=128)

    @validator("email")
    @classmethod
    def validate_account(cls, account: str) -> str:
        normalized = account.strip().lower()
        if "@" in normalized:
            return RegisterRequest.validate_email(normalized)
        if not ACCOUNT_RE.fullmatch(normalized):
            raise ValueError("valid account or email is required")
        return normalized


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True
