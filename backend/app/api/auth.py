from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.dependencies import DbSession, get_current_user
from app.models import PasswordResetToken, RefreshToken, User, UserRole
from app.notifications import send_email
from app.schemas import (
    AuthResponse,
    LoginRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    UpdateProfileRequest,
    UserResponse,
)
from app.security import create_access_token, create_opaque_token, hash_password, hash_token, verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
REFRESH_COOKIE = "refresh_token"


def normalize_email(email: str | None) -> str | None:
    return email.strip().lower() if email else None


def set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="strict",
        path="/api/v1/auth",
    )


async def persist_refresh_token(db: DbSession, user: User, request: Request) -> str:
    raw_token = create_opaque_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(days=get_settings().refresh_token_expire_days),
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    )
    return raw_token


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id, user.role), user=UserResponse.model_validate(user))


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, request: Request, response: Response, db: DbSession) -> AuthResponse:
    email = normalize_email(payload.email)
    phone = payload.phone.strip() if payload.phone else None
    existing = await db.scalar(select(User).where(or_(func.lower(User.email) == email if email else False, User.phone == phone if phone else False)))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="não foi possível criar a conta")
    user = User(full_name=payload.full_name.strip(), email=email, phone=phone, password_hash=hash_password(payload.password), role=UserRole.CUSTOMER)
    db.add(user)
    try:
        await db.flush()
        raw_refresh = await persist_refresh_token(db, user, request)
        if user.email:
            await send_email(
                db,
                user.email,
                "REGISTRATION_CONFIRMED",
                "Cadastro confirmado | Barbearia",
                f"<p>Olá, {user.full_name}.</p><p>Seu cadastro na barbearia foi confirmado.</p>",
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="não foi possível criar a conta") from exc
    set_refresh_cookie(response, raw_refresh)
    return auth_response(user)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, request: Request, response: Response, db: DbSession) -> AuthResponse:
    identifier = payload.identifier.strip()
    user = await db.scalar(select(User).where(or_(func.lower(User.email) == identifier.lower(), User.phone == identifier)))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        if user is not None:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = datetime.now(UTC) + timedelta(minutes=15)
            await db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="credenciais inválidas")
    if user.locked_until and user.locked_until > datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="conta temporariamente bloqueada")
    user.failed_login_attempts = 0
    user.locked_until = None
    raw_refresh = await persist_refresh_token(db, user, request)
    await db.commit()
    set_refresh_cookie(response, raw_refresh)
    return auth_response(user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(request: Request, response: Response, db: DbSession, refresh_token: Annotated[str | None, Cookie()] = None) -> AuthResponse:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sessão ausente")
    stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)).with_for_update())
    now = datetime.now(UTC)
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sessão inválida")
    user = await db.get(User, stored.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="sessão inválida")
    stored.revoked_at = now
    new_raw = await persist_refresh_token(db, user, request)
    await db.flush()
    replacement = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(new_raw)))
    stored.replaced_by_id = replacement.id if replacement else None
    await db.commit()
    set_refresh_cookie(response, new_raw)
    return auth_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response, db: DbSession, refresh_token: Annotated[str | None, Cookie()] = None) -> None:
    if refresh_token:
        stored = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(refresh_token)))
        if stored and stored.revoked_at is None:
            stored.revoked_at = datetime.now(UTC)
            await db.commit()
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


@router.get("/me", response_model=UserResponse)
async def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_me(payload: UpdateProfileRequest, user: Annotated[User, Depends(get_current_user)], db: DbSession) -> UserResponse:
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        updates["email"] = normalize_email(updates["email"])
    if "phone" in updates and updates["phone"]:
        updates["phone"] = updates["phone"].strip()
    if "password" in updates:
        updates["password_hash"] = hash_password(updates.pop("password"))
    for field, value in updates.items():
        setattr(user, field, value)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="dados já cadastrados") from exc
    return UserResponse.model_validate(user)


@router.post("/password-reset/request")
async def request_password_reset(payload: PasswordResetRequest, db: DbSession) -> dict[str, str]:
    user = await db.scalar(select(User).where(func.lower(User.email) == payload.email.strip().lower()))
    if user:
        raw_token = create_opaque_token()
        db.add(PasswordResetToken(user_id=user.id, token_hash=hash_token(raw_token), expires_at=datetime.now(UTC) + timedelta(minutes=30)))
        if user.email:
            reset_url = f"{get_settings().app_base_url}/reset-password?token={raw_token}"
            await send_email(
                db,
                user.email,
                "PASSWORD_RESET_REQUESTED",
                "Redefinição de senha | Barbearia",
                f"<p>Olá, {user.full_name}.</p><p><a href=\"{reset_url}\">Redefina sua senha</a>. O link expira em 30 minutos.</p>",
            )
        await db.commit()
    return {"message": "se os dados estiverem corretos, você receberá instruções para redefinir a senha"}


@router.post("/password-reset/confirm")
async def confirm_password_reset(payload: PasswordResetConfirm, db: DbSession) -> dict[str, str]:
    token = await db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(payload.token), PasswordResetToken.used_at.is_(None)))
    if token is None or token.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token inválido ou expirado")
    user = await db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token inválido ou expirado")
    user.password_hash = hash_password(payload.password)
    token.used_at = datetime.now(UTC)
    await db.commit()
    return {"message": "senha redefinida com sucesso"}
