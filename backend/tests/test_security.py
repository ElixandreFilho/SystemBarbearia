from uuid import uuid4

from app.models import UserRole
from app.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_is_not_reversible() -> None:
    password = "Senha-Forte-123"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash)
    assert not verify_password("senha-incorreta", password_hash)


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    token = create_access_token(user_id, UserRole.CUSTOMER)

    decoded_user_id, decoded_role = decode_access_token(token)

    assert decoded_user_id == user_id
    assert decoded_role == UserRole.CUSTOMER
