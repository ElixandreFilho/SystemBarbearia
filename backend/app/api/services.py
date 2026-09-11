from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.dependencies import DbSession, get_current_user, require_role
from app.models import Service, User, UserRole
from app.schemas import ServiceCreate, ServiceResponse, ServiceUpdate

router = APIRouter(tags=["services"])


@router.get("/api/v1/services", response_model=list[ServiceResponse])
async def list_active_services(
    _: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> list[Service]:
    result = await db.scalars(select(Service).where(Service.is_active.is_(True)).order_by(Service.name))
    return list(result)


@router.get("/api/v1/admin/services", response_model=list[ServiceResponse])
async def list_admin_services(
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> list[Service]:
    result = await db.scalars(select(Service).order_by(Service.is_active.desc(), Service.name))
    return list(result)


@router.post("/api/v1/admin/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreate,
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> Service:
    service = Service(**payload.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.patch("/api/v1/admin/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: UUID,
    payload: ServiceUpdate,
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> Service:
    service = await db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="serviço não encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(service, field, value)
    await db.commit()
    await db.refresh(service)
    return service


@router.delete("/api/v1/admin/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_service(
    service_id: UUID,
    _: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: DbSession,
) -> None:
    service = await db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="serviço não encontrado")
    service.is_active = False
    await db.commit()
