from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from database import get_db
from models.models import User
from schemas.schemas import BotLinkRequest, MessageResponse
from core.deps import verify_bot_token
from core.redis import get_value, delete_key, link_code_key

router = APIRouter(prefix="/bot", tags=["Bot"])


@router.post("/link", response_model=MessageResponse)
async def link_telegram(
    data: BotLinkRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token),
):
    """
    Привязать Telegram аккаунт к пользователю по link_code.
    Вызывается ботом при команде /link <code>.
    """
    redis_key = link_code_key(data.link_code)
    user_id_str = await get_value(redis_key)

    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Код недействителен или истёк",
        )

    user_id = int(user_id_str)

    # Проверяем что telegram_id не занят другим пользователем
    existing_result = await db.execute(
        select(User).where(User.telegram_id == data.telegram_id)
    )
    existing = existing_result.scalar_one_or_none()
    if existing and existing.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Этот Telegram аккаунт уже привязан к другому пользователю",
        )

    # Получаем пользователя
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Привязываем Telegram
    user.telegram_id = data.telegram_id
    if data.telegram_username:
        user.telegram_username = data.telegram_username
    user.last_seen = datetime.now(timezone.utc)

    await db.commit()

    # Удаляем использованный код из Redis
    await delete_key(redis_key)

    return MessageResponse(message=f"Telegram аккаунт успешно привязан к пользователю {user.name}")


@router.get("/user/{telegram_id}", response_model=dict)
async def get_user_by_telegram(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_bot_token),
):
    """
    Получить данные пользователя по telegram_id.
    Используется ботом для идентификации пользователя.
    """
    result = await db.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    return {
        "id": user.id,
        "group_id": user.group_id,
        "name": user.name,
        "role": user.role,
        "reminder_enabled": user.reminder_enabled,
    }
