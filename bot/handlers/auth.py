"""
Авторизация и middleware для бота.
Вместо хардкода ALLOWED_USERS — проверка по telegram_id в PostgreSQL.
"""
import functools
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from database.db import AsyncSessionLocal
from database import queries

logger = logging.getLogger(__name__)


async def get_current_user(telegram_id: int) -> Optional[dict]:
    """Получить пользователя из БД по telegram_id."""
    async with AsyncSessionLocal() as db:
        return await queries.get_user_by_telegram_id(db, telegram_id)


async def is_authorized(telegram_id: int) -> bool:
    """Проверить авторизацию пользователя (наличие в БД + привязка к группе)."""
    user = await get_current_user(telegram_id)
    return user is not None and user.get("group_id") is not None


def auth_command(func):
    """Декоратор авторизации для command handlers."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user = await get_current_user(user_id)

        if not user or not user.get("group_id"):
            await update.message.reply_text(
                "👋 Привет! Вы не зарегистрированы в системе.\n\n"
                "Для доступа к боту:\n"
                "1. Зарегистрируйтесь на сайте по инвайт-ссылке\n"
                "2. В личном кабинете получите код привязки\n"
                "3. Отправьте боту: /link <код>"
            )
            return

        # Сохраняем данные пользователя в контексте
        context.user_data["db_user"] = user
        context.user_data["group_id"] = user["group_id"]
        context.user_data["user_name"] = user["name"]

        # Обновляем last_seen
        async with AsyncSessionLocal() as db:
            await queries.update_user_last_seen(db, user["id"])

        return await func(update, context)
    return wrapper


def auth_callback(func):
    """Декоратор авторизации для callback query handlers."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        user_id = query.from_user.id
        user = await get_current_user(user_id)

        if not user or not user.get("group_id"):
            await query.answer(
                "Вы не зарегистрированы. Используйте /link для привязки аккаунта.",
                show_alert=True
            )
            return

        context.user_data["db_user"] = user
        context.user_data["group_id"] = user["group_id"]
        context.user_data["user_name"] = user["name"]

        return await func(update, context)
    return wrapper
