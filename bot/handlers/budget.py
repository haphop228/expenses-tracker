import calendar
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from handlers.auth import auth_callback
from database.db import AsyncSessionLocal
from database import queries
from keyboards.keyboards import (
    budget_keyboard, categories_keyboard, back_keyboard, main_menu_keyboard
)
from utils.formatters import format_amount


def _current_month() -> str:
    return datetime.now().strftime("%Y-%m")


@auth_callback
async def budget_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню бюджета."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("💰 Бюджет:", reply_markup=budget_keyboard())


@auth_callback
async def budget_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Просмотр текущего бюджета."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data["group_id"]
    month = _current_month()
    year, mon = map(int, month.split("-"))
    days_in_month = calendar.monthrange(year, mon)[1]
    today = datetime.now().day

    async with AsyncSessionLocal() as db:
        total_budget = await queries.get_budget(db, group_id, month)
        total_spent = await queries.get_total_spent_for_month(db, group_id, month, exclude_budget_excluded=True)
        by_cat = await queries.get_budget_by_category(db, group_id, month)

    lines = [f"💰 Бюджет на {month}\n"]

    if total_budget:
        remaining = total_budget - total_spent
        pct = (total_spent / total_budget * 100) if total_budget > 0 else 0
        days_left = days_in_month - today
        daily_left = remaining / days_left if days_left > 0 and remaining > 0 else 0

        # Прогноз
        daily_avg = total_spent / today if today > 0 else 0
        forecast = daily_avg * days_in_month

        lines.append(f"📊 Бюджет: <b>{format_amount(total_budget)} ₽</b>")
        lines.append(f"💸 Потрачено: <b>{format_amount(total_spent)} ₽</b> ({pct:.0f}%)")
        lines.append(f"✅ Остаток: <b>{format_amount(remaining)} ₽</b>")
        if days_left > 0:
            lines.append(f"📅 Осталось дней: {days_left}")
            lines.append(f"💡 В день можно: {format_amount(daily_left)} ₽")
        if forecast > 0:
            over = forecast - total_budget
            if over > 0:
                lines.append(f"⚠️ Прогноз: {format_amount(forecast)} ₽ (перерасход {format_amount(over)} ₽)")
            else:
                lines.append(f"✅ Прогноз: {format_amount(forecast)} ₽ (в рамках бюджета)")
    else:
        lines.append(f"💸 Потрачено: <b>{format_amount(total_spent)} ₽</b>")
        lines.append("ℹ️ Бюджет не установлен")

    if by_cat:
        lines.append("\nЛимиты по категориям:")
        for row in by_cat:
            emoji = row.get("emoji") or ""
            name = row.get("name") or "?"
            limit = float(row["amount"])
            lines.append(f"  {emoji} {name}: {format_amount(limit)} ₽")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=back_keyboard("budget")
    )


@auth_callback
async def budget_set_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало установки бюджета."""
    query = update.callback_query
    await query.answer()

    month = _current_month()
    context.user_data["state"] = "budget_set_amount"
    context.user_data["budget_month"] = month

    await query.edit_message_text(
        f"✏️ Введите бюджет на {month} (в рублях):\n"
        "Например: <code>50000</code>",
        parse_mode="HTML"
    )


async def budget_set_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода суммы бюджета."""
    state = context.user_data.get("state")
    if state != "budget_set_amount":
        return

    text = update.message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму, например: <code>50000</code>", parse_mode="HTML")
        return

    group_id = context.user_data["group_id"]
    month = context.user_data.get("budget_month", _current_month())

    async with AsyncSessionLocal() as db:
        await queries.set_budget(db, group_id, month, amount)

    context.user_data.pop("state", None)
    context.user_data.pop("budget_month", None)

    await update.message.reply_text(
        f"✅ Бюджет на {month} установлен: <b>{format_amount(amount)} ₽</b>",
        parse_mode="HTML",
        reply_markup=budget_keyboard()
    )


@auth_callback
async def budget_categories_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор категории для установки лимита."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        categories = await queries.get_all_categories(db, group_id)

    if not categories:
        await query.edit_message_text("Нет категорий.", reply_markup=back_keyboard("budget"))
        return

    context.user_data["state"] = "budget_cat_select"
    await query.edit_message_text(
        "🗂 Выберите категорию для установки лимита:",
        reply_markup=categories_keyboard(categories, callback_prefix="budcat")
    )


@auth_callback
async def budget_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Категория выбрана — запросить лимит."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        category = await queries.get_category_by_id(db, category_id, group_id)

    if not category:
        await query.edit_message_text("Категория не найдена.", reply_markup=back_keyboard("budget"))
        return

    context.user_data["budget_cat_id"] = category_id
    context.user_data["budget_cat_name"] = category["name"]
    context.user_data["state"] = "budget_set_cat_amount"
    context.user_data["budget_month"] = _current_month()

    emoji = category.get("emoji") or ""
    await query.edit_message_text(
        f"Категория: {emoji} {category['name']}\n\n"
        f"Введите лимит на {_current_month()} (в рублях):\n"
        "Например: <code>10000</code>",
        parse_mode="HTML"
    )


async def budget_cat_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода лимита по категории."""
    state = context.user_data.get("state")
    if state != "budget_set_cat_amount":
        return

    text = update.message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму.", parse_mode="HTML")
        return

    group_id = context.user_data["group_id"]
    month = context.user_data.get("budget_month", _current_month())
    cat_id = context.user_data.get("budget_cat_id")
    cat_name = context.user_data.get("budget_cat_name", "")

    async with AsyncSessionLocal() as db:
        await queries.set_budget_for_category(db, group_id, month, cat_id, amount)

    context.user_data.pop("state", None)
    context.user_data.pop("budget_cat_id", None)
    context.user_data.pop("budget_cat_name", None)
    context.user_data.pop("budget_month", None)

    await update.message.reply_text(
        f"✅ Лимит для «{cat_name}» на {month}: <b>{format_amount(amount)} ₽</b>",
        parse_mode="HTML",
        reply_markup=budget_keyboard()
    )


def get_budget_handlers():
    """Получить обработчики для регистрации."""
    return [
        CallbackQueryHandler(budget_menu, pattern="^budget$"),
        CallbackQueryHandler(budget_view, pattern="^budget_view$"),
        CallbackQueryHandler(budget_set_start, pattern="^budget_set$"),
        CallbackQueryHandler(budget_categories_start, pattern="^budget_categories$"),
        CallbackQueryHandler(budget_category_selected, pattern=r"^budcat_\d+$"),
    ]
