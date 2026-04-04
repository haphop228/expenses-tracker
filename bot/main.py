import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

from config import BOT_TOKEN
from handlers.start import get_start_handlers
from handlers.link import get_link_handlers
from handlers.expenses import (
    get_expense_handlers, expense_amount_input, expense_date_input
)
from handlers.statistics import get_statistics_handlers
from handlers.budget import (
    get_budget_handlers, budget_set_amount_input, budget_cat_amount_input
)
from handlers.management import (
    get_management_handlers,
    cat_add_name_input, cat_rename_input,
    edit_amount_input, edit_comment_input,
    reminder_set_time_input,
)
from keyboards.keyboards import main_menu_keyboard
from utils.scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общий обработчик текстовых сообщений — роутинг по состоянию FSM."""
    # Проверяем авторизацию
    from handlers.auth import is_authorized
    user_id = update.effective_user.id
    if not await is_authorized(user_id):
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "👋 Вы не зарегистрированы.\n\n"
                "Для доступа к боту получите инвайт-ссылку и зарегистрируйтесь на сайте,\n"
                "затем привяжите Telegram командой /link <код>"
            )
        return

    # Обновляем данные пользователя в контексте если их нет
    if "group_id" not in context.user_data:
        from handlers.auth import get_current_user
        user = await get_current_user(user_id)
        if user:
            context.user_data["db_user"] = user
            context.user_data["group_id"] = user["group_id"]
            context.user_data["user_name"] = user["name"]

    state = context.user_data.get("state")

    if state == "expense_amount":
        await expense_amount_input(update, context)
    elif state == "expense_date":
        await expense_date_input(update, context)
    elif state == "budget_set_amount":
        await budget_set_amount_input(update, context)
    elif state == "budget_set_cat_amount":
        await budget_cat_amount_input(update, context)
    elif state == "cat_add_name":
        await cat_add_name_input(update, context)
    elif state == "cat_rename_input":
        await cat_rename_input(update, context)
    elif state == "edit_amount":
        await edit_amount_input(update, context)
    elif state == "edit_comment":
        await edit_comment_input(update, context)
    elif state == "reminder_set_time":
        await reminder_set_time_input(update, context)
    else:
        if update.effective_chat.type == "private":
            await update.message.reply_text(
                "Используйте кнопки меню для навигации.",
                reply_markup=main_menu_keyboard()
            )


async def post_init(application):
    """Действия после инициализации бота."""
    logger.info("Бот инициализирован")
    setup_scheduler(application)
    logger.info("Планировщик настроен")


def main():
    """Точка входа."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан!")
        return

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Регистрация обработчиков
    for handler in get_start_handlers():
        application.add_handler(handler)

    for handler in get_link_handlers():
        application.add_handler(handler)

    for handler in get_expense_handlers():
        application.add_handler(handler)

    for handler in get_statistics_handlers():
        application.add_handler(handler)

    for handler in get_budget_handlers():
        application.add_handler(handler)

    for handler in get_management_handlers():
        application.add_handler(handler)

    # Общий обработчик текстовых сообщений (должен быть последним)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler)
    )

    logger.info("Бот запущен")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
