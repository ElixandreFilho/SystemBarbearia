import hashlib
from datetime import UTC, date, datetime, timedelta
from html import escape
from typing import Annotated
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.api.availability import get_availability
from app.dependencies import DbSession, get_current_user, require_role
from app.audit import record_audit
from app.models import Appointment, AppointmentService, AppointmentStatus, BarbershopSettings, IdempotencyRecord, Service, User, UserRole
from app.notifications import send_email
from app.schemas import AdminAppointmentCreate, AdminAppointmentResponse, AdminDashboardResponse, AppointmentCreate, AppointmentResponse, AppointmentUpdate, CancelAppointmentRequest, PopularServiceResponse

router = APIRouter(prefix="/api/v1/appointments", tags=["appointments"])
admin_router = APIRouter(prefix="/api/v1/admin/appointments", tags=["admin-appointments"])


def advisory_lock_key(target_date) -> int:
    digest = hashlib.sha256(target_date.isoformat().encode()).digest()
    return int.from_bytes(digest[:8], byteorder="big", signed=True)


def appointment_email_html(customer_name: str, appointment: Appointment, message: str) -> str:
    return f"""<div style=\"font-family:Arial,sans-serif;line-height:1.6;color:#0F1B2E\">
      <h2>Barbearia</h2>
      <p>Olá, {escape(customer_name)}.</p>
      <p>{escape(message)}</p>
      <p><strong>Data:</strong> {appointment.date.strftime('%d/%m/%Y')}<br>
      <strong>Horário:</strong> {appointment.start_time.strftime('%H:%M')}<br>
      <strong>Duração:</strong> {appointment.total_duration_minutes} minutos</p>
      <p>Até breve!</p>
    </div>"""


async def has_customer_overlap(
    db: DbSession,
    customer_id: UUID,
    target_date: date,
    start_time,
    end_time,
    exclude_appointment_id: UUID | None = None,
) -> bool:
    query = select(Appointment.id).where(
            Appointment.customer_id == customer_id,
            Appointment.date == target_date,
            Appointment.status.in_((AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)),
            Appointment.start_time < end_time,
            Appointment.end_time > start_time,
        )
    if exclude_appointment_id:
        query = query.where(Appointment.id != exclude_appointment_id)
    appointment_id = await db.scalar(query.limit(1))
    return appointment_id is not None


async def admin_appointment_response(db: DbSession, appointment: Appointment, possible_no_show: bool = False) -> dict:
    customer = await db.get(User, appointment.customer_id)
    service_names = list(await db.scalars(
        select(Service.name)
        .join(AppointmentService, AppointmentService.service_id == Service.id)
        .where(AppointmentService.appointment_id == appointment.id)
        .order_by(Service.name)
    ))
    return {
        "id": appointment.id,
        "customer_id": appointment.customer_id,
        "date": appointment.date,
        "start_time": appointment.start_time,
        "end_time": appointment.end_time,
        "status": appointment.status,
        "total_price_cents": appointment.total_price_cents,
        "total_duration_minutes": appointment.total_duration_minutes,
        "notes": appointment.notes,
        "customer_name": customer.full_name if customer else "Cliente removido",
        "service_names": service_names,
        "service_ids": list(await db.scalars(
            select(AppointmentService.service_id)
            .where(AppointmentService.appointment_id == appointment.id)
        )),
        "possible_no_show": possible_no_show,
    }


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
    if await has_customer_overlap(db, user.id, payload.date, payload.start_time, end_time):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="você já possui um agendamento nesse intervalo")
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
    if user.email:
        await send_email(
            db,
            user.email,
            "APPOINTMENT_CONFIRMED",
            "Agendamento confirmado | Barbearia",
            appointment_email_html(user.full_name, appointment, "Seu horário foi confirmado com sucesso."),
            {"appointment_id": str(appointment.id)},
        )
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
) -> list[dict]:
    query = select(Appointment).where(Appointment.customer_id == user.id).order_by(Appointment.date.desc(), Appointment.start_time.desc())
    if target_date:
        query = query.where(Appointment.date == target_date)
    if appointment_status:
        query = query.where(Appointment.status == appointment_status)
    appointments = list(await db.scalars(query))
    responses = []
    for appointment in appointments:
        service_ids = list(await db.scalars(
            select(AppointmentService.service_id)
            .where(AppointmentService.appointment_id == appointment.id)
        ))
        responses.append({
            "id": appointment.id,
            "customer_id": appointment.customer_id,
            "date": appointment.date,
            "start_time": appointment.start_time,
            "end_time": appointment.end_time,
            "status": appointment.status,
            "total_price_cents": appointment.total_price_cents,
            "total_duration_minutes": appointment.total_duration_minutes,
            "notes": appointment.notes,
            "service_ids": service_ids,
        })
    return responses


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
    if user.email:
        await send_email(
            db,
            user.email,
            "APPOINTMENT_CANCELLED",
            "Agendamento cancelado | Barbearia",
            appointment_email_html(user.full_name, appointment, "Seu agendamento foi cancelado."),
            {"appointment_id": str(appointment.id)},
        )
    await db.commit()


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_my_appointment(
    appointment_id: UUID,
    payload: AppointmentUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None or appointment.customer_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agendamento não encontrado")
    if appointment.status not in (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="agendamento não pode ser editado")

    await db.execute(select(func.pg_advisory_xact_lock(advisory_lock_key(appointment.date))))
    services = list(await db.scalars(select(Service).where(Service.id.in_(payload.service_ids), Service.is_active.is_(True))))
    if len(services) != len(set(payload.service_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="um ou mais serviços não estão disponíveis")
    duration = sum(service.duration_minutes for service in services)
    end_time = (datetime.combine(appointment.date, appointment.start_time) + timedelta(minutes=duration)).time()
    availability = await get_availability(user, db, appointment.date, payload.service_ids, exclude_appointment_id=appointment.id)
    if appointment.start_time not in availability.slots:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="o novo serviço não cabe nesse horário")
    if await has_customer_overlap(db, user.id, appointment.date, appointment.start_time, end_time, exclude_appointment_id=appointment.id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="você já possui um agendamento nesse intervalo")

    old_services = list(await db.scalars(select(AppointmentService).where(AppointmentService.appointment_id == appointment.id)))
    for item in old_services:
        await db.delete(item)
    db.add_all(
        AppointmentService(
            appointment_id=appointment.id,
            service_id=service.id,
            price_cents_snapshot=service.price_cents,
            duration_minutes_snapshot=service.duration_minutes,
        )
        for service in services
    )
    appointment.end_time = end_time
    appointment.total_price_cents = sum(service.price_cents for service in services)
    appointment.total_duration_minutes = duration
    appointment.notes = payload.notes
    await db.commit()
    await db.refresh(appointment)
    return appointment


@admin_router.get("", response_model=list[AdminAppointmentResponse])
async def list_admin_appointments(
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
    target_date: date | None = Query(default=None, alias="date"),
    appointment_status: AppointmentStatus | None = Query(default=None, alias="status"),
) -> list[Appointment]:
    query = select(Appointment).order_by(Appointment.date, Appointment.start_time)
    if target_date:
        query = query.where(Appointment.date == target_date)
    if appointment_status:
        query = query.where(Appointment.status == appointment_status)
    appointments = list(await db.scalars(query))
    settings = await db.get(BarbershopSettings, 1) or BarbershopSettings(id=1)
    now = datetime.now(ZoneInfo(settings.timezone))
    responses = []
    for appointment in appointments:
        appointment_end = datetime.combine(appointment.date, appointment.end_time, tzinfo=ZoneInfo(settings.timezone))
        possible_no_show = appointment.status == AppointmentStatus.CONFIRMED and appointment_end + timedelta(minutes=settings.no_show_grace_minutes) <= now
        responses.append(await admin_appointment_response(db, appointment, possible_no_show))
    return responses


@admin_router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_appointment(
    payload: AdminAppointmentCreate,
    request: Request,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> Appointment:
    customer = await db.scalar(select(User).where(User.id == payload.customer_id, User.role == UserRole.CUSTOMER, User.is_active.is_(True)))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cliente não encontrado")
    await db.execute(select(func.pg_advisory_xact_lock(advisory_lock_key(payload.date))))
    availability = await get_availability(customer, db, payload.date, payload.service_ids)
    if payload.start_time not in availability.slots:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="horário não está mais disponível")
    services = list(await db.scalars(select(Service).where(Service.id.in_(payload.service_ids), Service.is_active.is_(True))))
    if len(services) != len(set(payload.service_ids)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="um ou mais serviços não estão disponíveis")
    duration = sum(service.duration_minutes for service in services)
    end_time = (datetime.combine(payload.date, payload.start_time) + timedelta(minutes=duration)).time()
    if await has_customer_overlap(db, customer.id, payload.date, payload.start_time, end_time):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="este cliente já possui um agendamento nesse intervalo")
    appointment = Appointment(
        customer_id=customer.id,
        date=payload.date,
        start_time=payload.start_time,
        end_time=end_time,
        status=AppointmentStatus.CONFIRMED,
        total_price_cents=sum(service.price_cents for service in services),
        total_duration_minutes=duration,
        notes=payload.notes,
        created_by=admin.id,
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
    record_audit(db, request, admin.id, "APPOINTMENT_CREATED_FOR_CUSTOMER", "Appointment", str(appointment.id), {"customer_id": str(customer.id)})
    if customer.email:
        await send_email(
            db,
            customer.email,
            "APPOINTMENT_CONFIRMED",
            "Agendamento confirmado | Barbearia",
            appointment_email_html(customer.full_name, appointment, "Seu horário foi confirmado pela barbearia."),
            {"appointment_id": str(appointment.id)},
        )
    await db.commit()
    await db.refresh(appointment)
    return appointment


@admin_router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
    start_date: date | None = Query(default=None, alias="from"),
    end_date: date | None = Query(default=None, alias="to"),
) -> dict:
    query = select(Appointment)
    if start_date:
        query = query.where(Appointment.date >= start_date)
    if end_date:
        query = query.where(Appointment.date <= end_date)
    appointments = list(await db.scalars(query))
    active = [item for item in appointments if item.status != AppointmentStatus.CANCELLED]
    service_rows = await db.execute(
        select(Service.name, func.count(AppointmentService.id))
        .join(AppointmentService, AppointmentService.service_id == Service.id)
        .join(Appointment, Appointment.id == AppointmentService.appointment_id)
        .where(Appointment.status != AppointmentStatus.CANCELLED)
        .group_by(Service.name)
        .order_by(func.count(AppointmentService.id).desc())
        .limit(5)
    )
    return {
        "total_appointments": len(appointments),
        "confirmed_appointments": sum(item.status == AppointmentStatus.CONFIRMED for item in appointments),
        "completed_appointments": sum(item.status == AppointmentStatus.COMPLETED for item in appointments),
        "cancelled_appointments": sum(item.status == AppointmentStatus.CANCELLED for item in appointments),
        "total_revenue_cents": sum(item.total_price_cents for item in active),
        "popular_services": [PopularServiceResponse(name=name, bookings=bookings) for name, bookings in service_rows.all()],
    }


@admin_router.patch("/{appointment_id}/cancel", response_model=AppointmentResponse)
async def admin_cancel_appointment(
    appointment_id: UUID,
    payload: CancelAppointmentRequest,
    request: Request,
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
    record_audit(db, request, admin.id, "APPOINTMENT_CANCELLED", "Appointment", str(appointment.id), {"reason": payload.reason})
    customer = await db.get(User, appointment.customer_id)
    if customer and customer.email:
        await send_email(
            db,
            customer.email,
            "APPOINTMENT_CANCELLED",
            "Agendamento cancelado | Barbearia",
            appointment_email_html(customer.full_name, appointment, "Seu agendamento foi cancelado pela barbearia."),
            {"appointment_id": str(appointment.id), "reason": payload.reason},
        )
    await db.commit()
    await db.refresh(appointment)
    return appointment


@admin_router.patch("/{appointment_id}/complete", response_model=AppointmentResponse)
async def complete_appointment(
    appointment_id: UUID,
    request: Request,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> Appointment:
    appointment = await db.get(Appointment, appointment_id)
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agendamento não encontrado")
    if appointment.status != AppointmentStatus.CONFIRMED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="apenas agendamentos confirmados podem ser concluídos")
    appointment.status = AppointmentStatus.COMPLETED
    record_audit(db, request, admin.id, "APPOINTMENT_COMPLETED", "Appointment", str(appointment.id))
    await db.commit()
    await db.refresh(appointment)
    return appointment


@admin_router.patch("/{appointment_id}/no-show", response_model=AppointmentResponse)
async def mark_no_show(
    appointment_id: UUID,
    request: Request,
    admin: Annotated[User, Depends(require_role(UserRole.ADMIN))],
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
    record_audit(db, request, admin.id, "APPOINTMENT_NO_SHOW", "Appointment", str(appointment.id))
    await db.commit()
    await db.refresh(appointment)
    return appointment
