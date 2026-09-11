from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, require_role
from app.models import BarbershopSettings, BlockedSlot, BusinessHours, SpecialDate, User, UserRole
from app.schemas import (
    BlockedSlotCreate,
    BlockedSlotResponse,
    BusinessHoursItem,
    BusinessHoursResponse,
    SettingsResponse,
    SettingsUpdate,
    SpecialDateCreate,
    SpecialDateResponse,
    SpecialDateUpdate,
)

router = APIRouter(prefix="/api/v1/admin", tags=["schedule"])
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(_: AdminUser, db: DbSession) -> BarbershopSettings:
    settings = await db.get(BarbershopSettings, 1)
    if settings is None:
        settings = BarbershopSettings(id=1)
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
    return settings


@router.patch("/settings", response_model=SettingsResponse)
async def update_settings(payload: SettingsUpdate, _: AdminUser, db: DbSession) -> BarbershopSettings:
    settings = await db.get(BarbershopSettings, 1)
    if settings is None:
        settings = BarbershopSettings(id=1)
        db.add(settings)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await db.commit()
    await db.refresh(settings)
    return settings


@router.get("/business-hours", response_model=list[BusinessHoursResponse])
async def list_business_hours(_: AdminUser, db: DbSession) -> list[BusinessHours]:
    result = await db.scalars(select(BusinessHours).order_by(BusinessHours.weekday, BusinessHours.start_time))
    return list(result)


@router.put("/business-hours", response_model=list[BusinessHoursResponse])
async def replace_business_hours(payload: list[BusinessHoursItem], _: AdminUser, db: DbSession) -> list[BusinessHours]:
    await db.execute(delete(BusinessHours))
    rows = [BusinessHours(**item.model_dump()) for item in payload]
    db.add_all(rows)
    await db.commit()
    return rows


@router.get("/special-dates", response_model=list[SpecialDateResponse])
async def list_special_dates(_: AdminUser, db: DbSession) -> list[SpecialDate]:
    result = await db.scalars(select(SpecialDate).order_by(SpecialDate.date))
    return list(result)


@router.post("/special-dates", response_model=SpecialDateResponse, status_code=status.HTTP_201_CREATED)
async def create_special_date(payload: SpecialDateCreate, _: AdminUser, db: DbSession) -> SpecialDate:
    row = SpecialDate(**payload.model_dump())
    db.add(row)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="já existe uma exceção para esta data") from exc
    await db.refresh(row)
    return row


@router.patch("/special-dates/{special_date_id}", response_model=SpecialDateResponse)
async def update_special_date(special_date_id: UUID, payload: SpecialDateUpdate, _: AdminUser, db: DbSession) -> SpecialDate:
    row = await db.get(SpecialDate, special_date_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="data especial não encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/special-dates/{special_date_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_special_date(special_date_id: UUID, _: AdminUser, db: DbSession) -> None:
    row = await db.get(SpecialDate, special_date_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="data especial não encontrada")
    await db.delete(row)
    await db.commit()


@router.get("/blocked-slots", response_model=list[BlockedSlotResponse])
async def list_blocked_slots(_: AdminUser, db: DbSession, target_date: date | None = Query(default=None, alias="date")) -> list[BlockedSlot]:
    query = select(BlockedSlot).order_by(BlockedSlot.date, BlockedSlot.start_time)
    if target_date:
        query = query.where(BlockedSlot.date == target_date)
    result = await db.scalars(query)
    return list(result)


@router.post("/blocked-slots", response_model=BlockedSlotResponse, status_code=status.HTTP_201_CREATED)
async def create_blocked_slot(payload: BlockedSlotCreate, admin: AdminUser, db: DbSession) -> BlockedSlot:
    row = BlockedSlot(**payload.model_dump(), created_by=admin.id)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


@router.delete("/blocked-slots/{blocked_slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blocked_slot(blocked_slot_id: UUID, _: AdminUser, db: DbSession) -> None:
    row = await db.get(BlockedSlot, blocked_slot_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="bloqueio não encontrado")
    await db.delete(row)
    await db.commit()
