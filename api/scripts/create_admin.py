#!/usr/bin/env python3
"""
Скрипт для создания первого администратора сервиса.

Использование:
    python scripts/create_admin.py --login admin --password MySecurePass123

После создания выведет TOTP URI для настройки Google Authenticator.
"""
import asyncio
import argparse
import sys
import os

# Добавляем корень api/ в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select

from core.config import settings
from core.security import hash_password, generate_totp_secret, get_totp_uri
from models.models import Admin
from database import Base


async def create_admin(login: str, password: str) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as session:
        # Проверяем что такого логина нет
        result = await session.execute(select(Admin).where(Admin.login == login))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"❌ Администратор с логином '{login}' уже существует")
            await engine.dispose()
            return

        totp_secret = generate_totp_secret()
        admin = Admin(
            login=login,
            password_hash=hash_password(password),
            totp_secret=totp_secret,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)

        totp_uri = get_totp_uri(totp_secret, login)

        print(f"\n✅ Администратор создан:")
        print(f"   Логин: {login}")
        print(f"   ID: {admin.id}")
        print(f"\n🔐 TOTP секрет: {totp_secret}")
        print(f"\n📱 Добавьте в Google Authenticator:")
        print(f"   {totp_uri}")
        print(f"\n⚠️  Сохраните TOTP секрет в надёжном месте!")

    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Создать администратора сервиса")
    parser.add_argument("--login", required=True, help="Логин администратора")
    parser.add_argument("--password", required=True, help="Пароль (минимум 8 символов)")

    args = parser.parse_args()

    if len(args.password) < 8:
        print("❌ Пароль должен содержать минимум 8 символов")
        sys.exit(1)

    asyncio.run(create_admin(args.login, args.password))


if __name__ == "__main__":
    main()
