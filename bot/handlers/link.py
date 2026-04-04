"""
Хендлер команды /link <code> — привязка Telegram аккаунта к веб-аккаунту.
"""
import logging

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from database.db import AsyncSessionLocal
from database import queries
from keyboards.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /link <code>.
    
    Пользователь получает код в личном кабинете на сайте (15 мин TTL),
    затем отправляет боту: /link ABC12345
    """
    telegram_id = update.effective_user.id
    telegram_username = update.effective_user.username

    # Проверяем аргументы
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Укажите код привязки.\n\n"
            "Использование: /link <код>\n\n"
            "Код можно получить в личном кабинете на сайте.\n"
            "Код действителен 15 минут."
        )
        return

    link_code = context.args[0].strip().upper()

    # Проверяем не привязан ли уже этот telegram_id
    async with AsyncSessionLocal() as db:
        existing_user = await queries.get_user_by_telegram_id(db, telegram_id)
        if existing_user and existing_user.get("group_id"):
            await update.message.reply_text(
                f"✅ Ваш Telegram уже привязан к аккаунту <b>{existing_user['name']}</b>.\n\n"
                "Если хотите привязать другой аккаунт, обратитесь к администратору.",
                parse_mode="HTML",
                reply_markup=main_menu_keyboard(),
            )
            return

        # Привязываем аккаунт
        user = await queries.link_telegram_account(db, link_code, telegram_id, telegram_username)

    if not user:
        await update.message.reply_text(
            "❌ Код недействителен или истёк.\n\n"
            "Получите новый код в личном кабинете на сайте.\n"
            "Код действителен 15 минут."
        )
        return

    await update.message.reply_text(
        f"✅ Telegram успешно привязан к аккаунту <b>{user['name']}</b>!\n\n"
        "Теперь вы можете пользоваться ботом.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
    logger.info(f"Telegram {telegram_id} (@{telegram_username}) привязан к пользователю {user['id']}")


def get_link_handlers():
    """Получить обработчики для регистрации."""
    return [
        CommandHandler("link", link_command),
    ]
