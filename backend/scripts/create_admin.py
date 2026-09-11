import argparse
import asyncio

from sqlalchemy import select

from app.db import session_factory
from app.models import User, UserRole
from app.security import hash_password


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cria ou atualiza o administrador inicial.")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--phone")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    async with session_factory() as db:
        admin = await db.scalar(select(User).where(User.email == args.email.strip().lower()))
        if admin is None:
            admin = User(
                full_name=args.name.strip(),
                email=args.email.strip().lower(),
                phone=args.phone,
                password_hash=hash_password(args.password),
                role=UserRole.ADMIN,
            )
            db.add(admin)
        else:
            admin.full_name = args.name.strip()
            admin.phone = args.phone
            admin.password_hash = hash_password(args.password)
            admin.role = UserRole.ADMIN
            admin.is_active = True
        await db.commit()
        print(f"Administrador configurado: {admin.email}")


if __name__ == "__main__":
    asyncio.run(main())
