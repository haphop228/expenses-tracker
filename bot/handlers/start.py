from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from handlers.auth import auth_command, auth_callback, get_current_user
from keyboards.keyboards import main_menu_keyboard
from database.db import AsyncSessionLocal
from database import queries


@auth_command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user_name = context.user_data.get("user_name", update.effective_user.first_name)
    text = (
        f"👋 Привет, {user_name}!\n\n"
        "Я бот для учёта расходов. Помогу тебе и твоей группе "
        "отслеживать траты, контролировать бюджет и смотреть статистику.\n\n"
        "Выбери действие:"
    )
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())


@auth_command
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /menu."""
    context.user_data_keys_to_keep = {"db_user", "group_id", "user_name"}
    # Очищаем только FSM-состояние
    for key in list(context.user_data.keys()):
        if key not in ("db_user", "group_id", "user_name"):
            del context.user_data[key]
    await update.message.reply_text("📋 Главное меню:", reply_markup=main_menu_keyboard())


@auth_command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help."""
    text = (
        "📖 Справка по боту\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💸 <b>Добавить трату</b> — записать новый расход\n"
        "📊 <b>Статистика</b> — посмотреть траты за период\n"
        "💰 <b>Бюджет</b> — контроль бюджета и прогнозы\n"
        "⚙️ <b>Управление</b> — категории, редактирование, напоминания\n\n"
        "Команды:\n"
        "/start — приветствие и главное меню\n"
        "/menu — показать главное меню\n"
        "/help — эта справка\n"
        "/link <код> — привязать Telegram к аккаунту на сайте\n"
        "/cancel — отмена текущего действия"
    )
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=main_menu_keyboard())


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cancel."""
    for key in list(context.user_data.keys()):
        if key not in ("db_user", "group_id", "user_name"):
            del context.user_data[key]
    await update.message.reply_text("❌ Действие отменено.", reply_markup=main_menu_keyboard())


@auth_callback
async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню через callback."""
    query = update.callback_query
    await query.answer()
    for key in list(context.user_data.keys()):
        if key not in ("db_user", "group_id", "user_name"):
            del context.user_data[key]
    await query.edit_message_text("📋 Главное меню:", reply_markup=main_menu_keyboard())


def get_start_handlers():
    """Получить обработчики для регистрации."""
    return [
        CommandHandler("start", start_command),
        CommandHandler("menu", menu_command),
        CommandHandler("help", help_command),
        CommandHandler("cancel", cancel_command),
        CallbackQueryHandler(back_to_main_menu, pattern="^back_main$"),
    ]
