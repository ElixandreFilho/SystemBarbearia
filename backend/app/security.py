import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings
from app.models import UserRole

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False


def create_access_token(user_id: UUID, role: UserRole) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    expires = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "role": role.value, "iat": now, "exp": expires}, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> tuple[UUID, UserRole]:
    payload = jwt.decode(token, get_settings().jwt_secret_key, algorithms=["HS256"])
    return UUID(payload["sub"]), UserRole(payload["role"])


def create_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
