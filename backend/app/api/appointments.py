import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.availability import get_availability
from app.dependencies import DbSession, get_current_user
from app.models import Appointment, AppointmentService, AppointmentStatus, IdempotencyRecord, Service, User
from app.schemas import AppointmentCreate, AppointmentResponse

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])


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
