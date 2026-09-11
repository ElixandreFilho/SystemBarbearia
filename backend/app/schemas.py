from datetime import date, datetime, time
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


class ServiceBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_cents: int = Field(ge=0)
    duration_minutes: int = Field(gt=0, le=1440)


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    price_cents: int | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    is_active: bool | None = None


class ServiceResponse(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class SettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    timezone: str
    capacity: int
    booking_window_days: int
    min_cancellation_notice_minutes: int
    no_show_grace_minutes: int
    slot_granularity_minutes: int
    updated_at: datetime


class SettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    timezone: str | None = Field(default=None, min_length=3, max_length=64)
    capacity: int | None = Field(default=None, ge=1, le=100)
    booking_window_days: int | None = Field(default=None, ge=0, le=30)
    min_cancellation_notice_minutes: int | None = Field(default=None, ge=0, le=10080)
    no_show_grace_minutes: int | None = Field(default=None, ge=0, le=1440)
    slot_granularity_minutes: int | None = Field(default=None, ge=5, le=60)


class BusinessHoursItem(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def validate_interval(self) -> "BusinessHoursItem":
        if self.start_time >= self.end_time:
            raise ValueError("o horário inicial deve ser anterior ao final")
        return self


class BusinessHoursResponse(BusinessHoursItem):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class SpecialDateBase(BaseModel):
    date: date
    is_closed: bool = False
    custom_open_time: time | None = None
    custom_close_time: time | None = None
    label: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_schedule(self) -> "SpecialDateBase":
        if self.is_closed and (self.custom_open_time or self.custom_close_time):
            raise ValueError("data fechada não pode ter horário customizado")
        if not self.is_closed and ((self.custom_open_time is None) != (self.custom_close_time is None)):
            raise ValueError("informe abertura e fechamento customizados")
        if self.custom_open_time and self.custom_close_time and self.custom_open_time >= self.custom_close_time:
            raise ValueError("o horário inicial deve ser anterior ao final")
        return self


class SpecialDateCreate(SpecialDateBase):
    pass


class SpecialDateUpdate(BaseModel):
    is_closed: bool | None = None
    custom_open_time: time | None = None
    custom_close_time: time | None = None
    label: str | None = Field(default=None, max_length=160)


class SpecialDateResponse(SpecialDateBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class BlockedSlotBase(BaseModel):
    date: date
    start_time: time
    end_time: time
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_interval(self) -> "BlockedSlotBase":
        if self.start_time >= self.end_time:
            raise ValueError("o horário inicial deve ser anterior ao final")
        return self


class BlockedSlotCreate(BlockedSlotBase):
    pass


class BlockedSlotResponse(BlockedSlotBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by: UUID


class AvailabilityResponse(BaseModel):
    date: date
    duration_minutes: int
    slots: list[time]


class AppointmentCreate(BaseModel):
    date: date
    start_time: time
    service_ids: list[UUID] = Field(min_length=1)
    notes: str | None = Field(default=None, max_length=2000)


class AppointmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    date: date
    start_time: time
    end_time: time
    status: str
    total_price_cents: int
    total_duration_minutes: int
    notes: str | None


class CancelAppointmentRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    password: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def require_contact(self) -> "CustomerCreate":
        if not self.email and not self.phone:
            raise ValueError("informe e-mail ou telefone")
        return self


class CustomerUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=30)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None
