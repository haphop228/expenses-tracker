"""
Хендлер команды /link <code> — привязка Telegram аккаунта к веб-аккаунту.
Бот вызывает API POST /api/v1/bot/link, который проверяет код в Redis.
"""
import logging
import httpx

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from config import API_URL, BOT_API_SECRET
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

    # Вызываем API для привязки
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{API_URL}/bot/link",
                json={
                    "link_code": link_code,
                    "telegram_id": telegram_id,
                    "telegram_username": telegram_username,
                },
                headers={"X-Bot-Token": BOT_API_SECRET},
            )
    except httpx.RequestError as e:
        logger.error(f"Ошибка запроса к API: {e}")
        await update.message.reply_text(
            "❌ Ошибка связи с сервером. Попробуйте позже."
        )
        return

    if response.status_code == 200:
        data = response.json()
        await update.message.reply_text(
            f"✅ Telegram успешно привязан!\n\n"
            f"{data.get('message', 'Аккаунт привязан.')}\n\n"
            "Теперь вы можете пользоваться ботом.",
            reply_markup=main_menu_keyboard(),
        )
        logger.info(f"Telegram {telegram_id} (@{telegram_username}) привязан через API")

    elif response.status_code == 400:
        await update.message.reply_text(
            "❌ Код недействителен или истёк.\n\n"
            "Получите новый код в личном кабинете на сайте.\n"
            "Код действителен 15 минут."
        )
    elif response.status_code == 409:
        await update.message.reply_text(
            "⚠️ Этот Telegram аккаунт уже привязан к другому пользователю.\n\n"
            "Обратитесь к администратору."
        )
    else:
        logger.error(f"API вернул {response.status_code}: {response.text}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
        )


def get_link_handlers():
    """Получить обработчики для регистрации."""
    return [
        CommandHandler("link", link_command),
    ]
