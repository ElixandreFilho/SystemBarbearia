import hashlib
from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.availability import get_availability
from app.dependencies import DbSession, get_current_user, require_role
from app.models import Appointment, AppointmentService, AppointmentStatus, BarbershopSettings, IdempotencyRecord, Service, User, UserRole
from app.schemas import AppointmentCreate, AppointmentResponse, CancelAppointmentRequest

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])
admin_router = APIRouter(prefix="/api/v1/admin/appointments", tags=["admin-appointments"])


def advisory_lock_key(target_date) -> int:
    digest = hashlib.sha256(target_date.isoformat().encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    payload: AppointmentCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> Appointment:
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key é obrigatório")
    if len(idempotency_key) > 100:
        raise HTTPException(status_code=400, detail="Idempotency-Key inválido")

    existing_request = await db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user.id, IdempotencyRecord.key == idempotency_key))
    if existing_request:
        appointment = await db.get(Appointment, existing_request.appointment_id)
        if appointment:
            return appointment

    await db.execute(select(func.pg_advisory_xact_lock(advisory_lock_key(payload.date))))
    existing_request = await db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.user_id == user.id, IdempotencyRecord.key == idempotency_key))
    if existing_request:
        appointment = await db.get(Appointment, existing_request.appointment_id)
        if appointment:
            return appointment

    availability = await get_availability(user, db, payload.date, payload.service_ids)
    if payload.start_time not in availability.slots:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="horário não está mais disponível")

    services = list(await db.scalars(select(Service).where(Service.id.in_(payload.service_ids), Service.is_active.is_(True))))
    duration = sum(service.duration_minutes for service in services)
    total_price = sum(service.price_cents for service in services)
    end_time = (datetime.combine(payload.date, payload.start_time) + timedelta(minutes=duration)).time()
    appointment = Appointment(
        customer_id=user.id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=end_time,
        status=AppointmentStatus.CONFIRMED,
        total_price_cents=total_price,
        total_duration_minutes=duration,
        notes=payload.notes,
        created_by=user.id,
    )
    db.add(appointment)
    await db.flush()
    db.add_all(
        AppointmentService(
            appointment_id=appointment.id,
            service_id=service.id,
            price_cents_snapshot=service.price_cents,
            duration_minutes_snapshot=service.duration_minutes,
        )
        for service in services
    )
    db.add(IdempotencyRecord(user_id=user.id, key=idempotency_key, appointment_id=appointment.id))
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="requisição duplicada ou inválida") from exc
    await db.refresh(appointment)
    return appointment


@router.get("/me", response_model=list[AppointmentResponse])
async def list_my_appointments(
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    target_date: date | None = Query(default=None, alias="date"),
    appointment_status: AppointmentStatus | None = Query(default=None, alias="status"),
) -> list[Appointment]:
    query = select(Appointment).where(Appointment.customer_id == user.id).order_by(Appointment.date.desc(), Appointment.start_time.desc())
    if target_date:
        query = query.where(Appointment.date == target_date)
    if appointment_status:
        query = query.where(Appointment.status == appointment_status)
    return list(await db.scalars(query))


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_my_appointment(
    appointment_id: UUID,
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> None:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None or appointment.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agendamento não encontrado")
    if appointment.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agendamento não pode ser cancelado")
    settings = await db.get(BarbershopSettings, 1) or BarbershopSettings(id=1)
    appointment_start = datetime.combine(appointment.date, appointment.start_time, tzinfo=ZoneInfo(settings.timezone))
    if appointment_start - datetime.now(ZoneInfo(settings.timezone)) < timedelta(minutes=settings.min_cancellation_notice_minutes):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="o prazo mínimo para cancelamento foi ultrapassado")
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.now(UTC)
    appointment.cancelled_by = user.id
    await db.commit()


@admin_router.get("", response_model=list[AppointmentResponse])
async def list_admin_appointments(
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
    target_date: date | None = Query(default=None, alias="date"),
    appointment_status: AppointmentStatus | None = Query(default=None, alias="status"),
) -> list[Appointment]:
    query = select(Appointment).order_by(Appointment.date, Appointment.start_time)
    if target_date:
        query = query.where(Appointment.date == target_date)
    if appointment_status:
        query = query.where(Appointment.status == appointment_status)
    return list(await db.scalars(query))


@admin_router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def admin_cancel_appointment(
    appointment_id: UUID,
    payload: CancelAppointmentRequest,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agendamento não encontrado")
    if appointment.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agendamento não pode ser cancelado")
    appointment.status = AppointmentStatus.CANCELLED
    appointment.cancelled_at = datetime.now(UTC)
    appointment.cancelled_by = admin.id
    appointment.cancellation_reason = payload.reason
    await db.commit()
    await db.refresh(appointment)
    return appointment


@admin_router.patch("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: UUID,
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agendamento não encontrado")
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="apenas agendamentos confirmados podem ser concluídos")
    appointment.status = AppointmentStatus.COMPLETED
    await db.commit()
    await db.refresh(appointment)
    return appointment


@admin_router.patch("/{appointment_id}/no-show", response_model=AppointmentResponse)
async def mark_no_show(
    appointment_id: UUID,
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agendamento não encontrado")
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="apenas agendamentos confirmados podem virar no-show")
    settings = await db.get(BarbershopSettings, 1) or BarbershopSettings(id=1)
    appointment_end = datetime.combine(appointment.date, appointment.end_time, tzinfo=ZoneInfo(settings.timezone))
    if appointment_end + timedelta(minutes=settings.no_show_grace_minutes) > datetime.now(ZoneInfo(settings.timezone)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="o horário ainda não ultrapassou a tolerância de no-show")
    appointment.status = AppointmentStatus.NO_SHOW
    await db.commit()
    await db.refresh(appointment)
    return appointment
