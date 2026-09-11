from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.dependencies import DbSession, require_role
from app.audit import record_audit
from app.models import User, UserRole
from app.schemas import CustomerCreate, CustomerUpdate, UserResponse
from app.security import hash_password

router = APIRouter(prefix="/api/v1/admin/customers", tags=["admin-customers"])
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]


def normalize_email(email: str | None) -> str | None:
    return email.strip().lower() if email else None


@router.get("", response_model=list[UserResponse])
async def list_customers(
    _: AdminUser,
    db: DbSession,
    search: str | None = Query(default=None, max_length=120),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[User]:
    query = select(User).where(User.role == UserRole.CUSTOMER).order_by(User.created_at.desc()).offset(offset).limit(limit)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(User.full_name.ilike(pattern), User.email.ilike(pattern), User.phone.ilike(pattern)))
    return list(await db.scalars(query))


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_customer(payload: CustomerCreate, request: Request, admin: AdminUser, db: DbSession) -> User:
    email = normalize_email(payload.email)
    phone = payload.phone.strip() if payload.phone else None
    existing = await db.scalar(select(User).where(or_(func.lower(User.email) == email if email else False, User.phone == phone if phone else False)))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="não foi possível criar o cliente")
    customer = User(
        full_name=payload.full_name.strip(),
        email=email,
        phone=phone,
        password_hash=hash_password(payload.password),
        role=UserRole.CUSTOMER,
    )
    db.add(customer)
    record_audit(db, request, admin.id, "CUSTOMER_CREATED", "User", metadata={"email": email, "phone": phone})
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="não foi possível criar o cliente") from exc
    await db.refresh(customer)
    return customer


@router.get("/{customer_id}", response_model=UserResponse)
async def get_customer(customer_id: UUID, _: AdminUser, db: DbSession) -> User:
    customer = await db.scalar(select(User).where(User.id == customer_id, User.role == UserRole.CUSTOMER))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cliente não encontrado")
    return customer


@router.patch("/{customer_id}", response_model=UserResponse)
async def update_customer(customer_id: UUID, payload: CustomerUpdate, request: Request, admin: AdminUser, db: DbSession) -> User:
    customer = await db.scalar(select(User).where(User.id == customer_id, User.role == UserRole.CUSTOMER))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cliente não encontrado")
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        updates["email"] = normalize_email(updates["email"])
    if "phone" in updates and updates["phone"]:
        updates["phone"] = updates["phone"].strip()
    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
    for field, value in updates.items():
        setattr(customer, field, value)
    record_audit(db, request, admin.id, "CUSTOMER_UPDATED", "User", str(customer.id), {"fields": list(updates)})
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="dados já cadastrados") from exc
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_customer(customer_id: UUID, request: Request, admin: AdminUser, db: DbSession) -> None:
    customer = await db.scalar(select(User).where(User.id == customer_id, User.role == UserRole.CUSTOMER))
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="cliente não encontrado")
    customer.is_active = False
    record_audit(db, request, admin.id, "CUSTOMER_DEACTIVATED", "User", str(customer.id))
    await db.commit()
