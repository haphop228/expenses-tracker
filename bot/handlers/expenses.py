import re
import calendar
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from handlers.auth import auth_callback
from database.db import AsyncSessionLocal
from database import queries
from keyboards.keyboards import (
    categories_keyboard, confirm_expense_keyboard, main_menu_keyboard
)
from utils.formatters import format_amount, format_date, get_user_display_name


def _parse_amount_and_comment(text: str):
    """Парсинг строки вида '180, велосипед' или '180 велосипед' или '180-велосипед'."""
    text = text.strip()

    if "," in text:
        parts = text.split(",", 1)
        amount_str = parts[0].strip().replace(",", ".")
        comment = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    elif "-" in text and not text.startswith("-"):
        parts = text.split("-", 1)
        amount_str = parts[0].strip().replace(",", ".")
        comment = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    elif " " in text:
        parts = text.split(None, 1)
        amount_str = parts[0].strip().replace(",", ".")
        try:
            float(amount_str)
            comment = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
        except ValueError:
            return None, None
    else:
        amount_str = text.replace(",", ".")
        comment = None

    try:
        amount = float(amount_str)
    except ValueError:
        return None, None

    return amount, comment


@auth_callback
async def add_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления траты — показать категории."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        categories = await queries.get_all_categories(db, group_id)

    if not categories:
        await query.edit_message_text(
            "Нет категорий. Сначала добавьте категорию в разделе Управление.",
            reply_markup=main_menu_keyboard()
        )
        return

    context.user_data["state"] = "expense_category"
    await query.edit_message_text(
        "💸 Выберите категорию:",
        reply_markup=categories_keyboard(categories, callback_prefix="expcat")
    )


@auth_callback
async def expense_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Категория выбрана — запросить сумму и комментарий."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        category = await queries.get_category_by_id(db, category_id, group_id)

    if not category:
        await query.edit_message_text("Категория не найдена.", reply_markup=main_menu_keyboard())
        return

    context.user_data["expense_category_id"] = category_id
    context.user_data["expense_category_name"] = category["name"]
    context.user_data["expense_category_emoji"] = category.get("emoji") or ""
    context.user_data["state"] = "expense_amount"

    emoji = category.get("emoji") or ""
    prefix = f"{emoji} " if emoji else ""
    await query.edit_message_text(
        f"Категория: {prefix}{category['name']}\n\n"
        "Введите сумму и комментарий (необязательно):\n"
        "Примеры: <code>350</code>, <code>1500 продукты</code>, <code>280, кофе</code>",
        parse_mode="HTML"
    )


async def expense_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода суммы и комментария."""
    state = context.user_data.get("state")
    if state != "expense_amount":
        return

    text = update.message.text.strip()
    amount, comment = _parse_amount_and_comment(text)

    if amount is None:
        await update.message.reply_text(
            "❌ Введите корректную сумму, например: <code>350</code> или <code>1500, продукты</code>",
            parse_mode="HTML"
        )
        return

    if amount <= 0:
        await update.message.reply_text("❌ Сумма должна быть больше нуля.")
        return

    context.user_data["expense_amount"] = amount
    context.user_data["expense_comment"] = comment
    context.user_data["expense_date"] = None
    context.user_data["state"] = "expense_confirm"

    await _show_expense_confirmation(update.message, context)


async def _show_expense_confirmation(message_or_query, context, is_edit=False):
    """Показать карточку подтверждения траты."""
    user_name = context.user_data.get("user_name", "Вы")
    cat_emoji = context.user_data.get("expense_category_emoji") or ""
    cat_name = context.user_data.get("expense_category_name", "")
    amount = context.user_data.get("expense_amount", 0)
    comment = context.user_data.get("expense_comment")
    expense_date = context.user_data.get("expense_date")

    date_str = expense_date if expense_date else datetime.now().strftime("%Y-%m-%d")

    prefix = f"{cat_emoji} " if cat_emoji else ""
    lines = [f"{prefix}{cat_name} — {format_amount(amount)} ₽"]
    if comment:
        lines.append(f"💬 {comment}")
    lines.append(f"👤 {user_name}  📅 {format_date(date_str)}")

    text = "\n".join(lines)

    if is_edit:
        await message_or_query.edit_message_text(text, reply_markup=confirm_expense_keyboard())
    else:
        await message_or_query.reply_text(text, reply_markup=confirm_expense_keyboard())


@auth_callback
async def expense_set_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пользователь хочет указать дату."""
    query = update.callback_query
    await query.answer()

    now = datetime.now()

    context.user_data["state"] = "expense_date"
    await query.edit_message_text(
        f"📅 Введите дату в формате ДД.ММ.ГГГГ (например, 25.12.2023)\n"
        f"Или просто число текущего месяца (например, 15):\n"
        f"Текущий месяц: {now.strftime('%Y-%m')}"
    )


async def expense_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода даты."""
    state = context.user_data.get("state")
    if state != "expense_date":
        return

    text = update.message.text.strip()
    now = datetime.now()

    date_str = None

    try:
        if "." in text:
            dt = datetime.strptime(text, "%d.%m.%Y")
            date_str = dt.strftime("%Y-%m-%d")
        elif "-" in text:
            if len(text.split("-")[0]) == 4:
                dt = datetime.strptime(text, "%Y-%m-%d")
            else:
                dt = datetime.strptime(text, "%d-%m-%Y")
            date_str = dt.strftime("%Y-%m-%d")
        else:
            day = int(text)
            days_in_month = calendar.monthrange(now.year, now.month)[1]
            if day < 1 or day > days_in_month:
                raise ValueError
            date_str = f"{now.year}-{now.month:02d}-{day:02d}"
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат даты.\n"
            "Введите дату в формате ДД.ММ.ГГГГ (например, 25.12.2023) "
            "или просто число текущего месяца."
        )
        return

    context.user_data["expense_date"] = date_str
    context.user_data["state"] = "expense_confirm"

    await _show_expense_confirmation(update.message, context)


@auth_callback
async def expense_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение и сохранение траты."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data.get("group_id")
    db_user = context.user_data.get("db_user", {})
    user_id = db_user.get("id")
    category_id = context.user_data.get("expense_category_id")
    amount = context.user_data.get("expense_amount")
    comment = context.user_data.get("expense_comment")
    expense_date = context.user_data.get("expense_date")

    if not category_id or not amount:
        await query.edit_message_text("❌ Ошибка. Попробуйте заново.", reply_markup=main_menu_keyboard())
        return

    created_at = None
    if expense_date:
        now = datetime.now()
        created_at = datetime.strptime(expense_date, "%Y-%m-%d").replace(
            hour=now.hour, minute=now.minute, second=now.second
        )

    async with AsyncSessionLocal() as db:
        await queries.add_expense(db, group_id, user_id, category_id, amount, comment, created_at)

    # Очищаем FSM-состояние
    for key in list(context.user_data.keys()):
        if key not in ("db_user", "group_id", "user_name"):
            del context.user_data[key]

    await query.edit_message_text("✅ Трата записана!", reply_markup=main_menu_keyboard())


@auth_callback
async def expense_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления траты."""
    query = update.callback_query
    await query.answer()

    for key in list(context.user_data.keys()):
        if key not in ("db_user", "group_id", "user_name"):
            del context.user_data[key]
    await query.edit_message_text("❌ Отменено.", reply_markup=main_menu_keyboard())


@auth_callback
async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Общая отмена через callback."""
    query = update.callback_query
    await query.answer()

    for key in list(context.user_data.keys()):
        if key not in ("db_user", "group_id", "user_name"):
            del context.user_data[key]
    await query.edit_message_text("📋 Главное меню:", reply_markup=main_menu_keyboard())


def get_expense_handlers():
    """Получить обработчики для регистрации."""
    return [
        CallbackQueryHandler(add_expense_start, pattern="^add_expense$"),
        CallbackQueryHandler(expense_category_selected, pattern=r"^expcat_\d+$"),
        CallbackQueryHandler(expense_set_date, pattern="^set_expense_date$"),
        CallbackQueryHandler(expense_confirm, pattern="^confirm_expense$"),
        CallbackQueryHandler(expense_cancel, pattern="^cancel_expense$"),
        CallbackQueryHandler(cancel_callback, pattern="^cancel$"),
    ]
