from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import User, UserRole
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="credenciais inválidas")
    if credentials is None:
        raise unauthorized
    try:
        user_id, _ = decode_access_token(credentials.credentials)
    except Exception as exc:
        raise unauthorized from exc
    user = await db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise unauthorized
    return user


def require_role(role: UserRole):
    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acesso não autorizado")
        return user

    return dependency
