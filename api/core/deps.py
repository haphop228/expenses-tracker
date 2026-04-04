from typing import Optional
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.models import User, Admin
from core.security import decode_token

# Bearer token схема
bearer_scheme = HTTPBearer(auto_error=False)


# ==================== Пользователи ====================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Получить текущего пользователя из JWT токена."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Необходима авторизация",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    # Проверяем тип токена
    if payload.get("type") != "access":
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Получаем пользователя из БД
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    # Обновляем last_seen
    user.last_seen = datetime.now(timezone.utc)
    await db.commit()

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Проверить что пользователь активен (имеет группу)."""
    if not current_user.group_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь не привязан к группе",
        )
    return current_user


async def require_group_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Проверить что пользователь — администратор своей группы."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора группы",
        )
    return current_user


# ==================== Администраторы сервиса ====================

async def get_current_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Admin:
    """Получить текущего администратора сервиса из JWT токена."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Требуется авторизация администратора",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    payload = decode_token(credentials.credentials)
    if not payload:
        raise credentials_exception

    # Проверяем тип токена — должен быть admin
    if payload.get("type") != "admin" or payload.get("role") != "service_admin":
        raise credentials_exception

    admin_id: Optional[str] = payload.get("sub")
    if not admin_id:
        raise credentials_exception

    result = await db.execute(select(Admin).where(Admin.id == int(admin_id)))
    admin = result.scalar_one_or_none()

    if not admin:
        raise credentials_exception

    return admin


# ==================== Bot-to-API ====================

from fastapi import Header
from core.config import settings


async def verify_bot_token(
    x_bot_token: Optional[str] = Header(None, alias="X-Bot-Token"),
) -> bool:
    """Проверить токен бота для внутренних запросов Bot → API."""
    if not x_bot_token or x_bot_token != settings.BOT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен бота",
        )
    return True
