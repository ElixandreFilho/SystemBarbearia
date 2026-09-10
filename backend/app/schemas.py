from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import UserRole


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def require_contact(self) -> "RegisterRequest":
        if not self.email and not self.phone:
            raise ValueError("informe e-mail ou telefone")
        return self


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: str | None
    phone: str | None
    role: UserRole
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=20)
    password: str = Field(min_length=8, max_length=128)


class HealthResponse(BaseModel):
    status: str
    environment: str
    database: str = "not_checked"
