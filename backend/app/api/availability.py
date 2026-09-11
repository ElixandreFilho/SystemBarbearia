from datetime import date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.dependencies import DbSession, get_current_user
from app.models import Appointment, AppointmentStatus, BarbershopSettings, BlockedSlot, BusinessHours, Service, SpecialDate, User
from app.schemas import AvailabilityResponse
from app.schedule.availability import TimeInterval, generate_candidate_slots, max_concurrent_overlaps, subtract_intervals

router = APIRouter(prefix="/api/v1", tags=["availability"])


@router.get("/availability", response_model=AvailabilityResponse)
async def get_availability(
    _: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    target_date: date = Query(alias="date"),
    service_ids: list[UUID] = Query(min_length=1),
) -> AvailabilityResponse:
    services = list(await db.scalars(select(Service).where(Service.id.in_(service_ids), Service.is_active.is_(True))))
    if len(services) != len(set(service_ids)):
        raise HTTPException(status_code=400, detail="um ou mais serviços não estão disponíveis")
    duration = sum(service.duration_minutes for service in services)
    settings = await db.get(BarbershopSettings, 1)
    if settings is None:
        settings = BarbershopSettings(id=1)
    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    if target_date < now.date() or (target_date - now.date()).days > settings.booking_window_days:
        return AvailabilityResponse(date=target_date, duration_minutes=duration, slots=[])

    special = await db.scalar(select(SpecialDate).where(SpecialDate.date == target_date))
    if special and special.is_closed:
        return AvailabilityResponse(date=target_date, duration_minutes=duration, slots=[])
    if special and special.custom_open_time and special.custom_close_time:
        windows = [TimeInterval(special.custom_open_time, special.custom_close_time)]
    else:
        weekday_hours = list(await db.scalars(select(BusinessHours).where(BusinessHours.weekday == target_date.weekday()).order_by(BusinessHours.start_time)))
        windows = [TimeInterval(row.start_time, row.end_time) for row in weekday_hours]

    blocks = list(await db.scalars(select(BlockedSlot).where(BlockedSlot.date == target_date)))
    open_windows = [segment for window in windows for segment in subtract_intervals(window, [TimeInterval(row.start_time, row.end_time) for row in blocks])]
    slots = generate_candidate_slots(
        open_windows,
        duration,
        settings.slot_granularity_minutes,
        now=now.replace(tzinfo=None) if target_date == now.date() else None,
        target_date=target_date,
    )

    active_statuses = (AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED)
    appointments = list(await db.scalars(select(Appointment).where(Appointment.date == target_date, Appointment.status.in_(active_statuses))))
    existing = [TimeInterval(item.start_time, item.end_time) for item in appointments]
    valid_slots = []
    for slot in slots:
        end_dt = datetime.combine(target_date, slot) + timedelta(minutes=duration)
        candidate = TimeInterval(slot, end_dt.time())
        if max_concurrent_overlaps(candidate, existing) < settings.capacity:
            valid_slots.append(slot)
    return AvailabilityResponse(date=target_date, duration_minutes=duration, slots=valid_slots)
