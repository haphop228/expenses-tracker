from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from handlers.auth import auth_callback
from database.db import AsyncSessionLocal
from database import queries
from keyboards.keyboards import (
    management_keyboard, categories_manage_keyboard, category_actions_keyboard,
    expense_actions_keyboard, categories_keyboard, back_keyboard,
    main_menu_keyboard, confirm_delete_keyboard
)
from utils.formatters import format_amount, format_date


# ==================== Управление ====================

@auth_callback
async def management_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню управления."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚙️ Управление:", reply_markup=management_keyboard())


# ==================== Категории ====================

@auth_callback
async def manage_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список категорий для управления."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        categories = await queries.get_all_categories(db, group_id)

    await query.edit_message_text(
        "📋 Категории:",
        reply_markup=categories_manage_keyboard(categories)
    )


@auth_callback
async def category_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия с категорией."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        category = await queries.get_category_by_id(db, category_id, group_id)

    if not category:
        await query.edit_message_text("Категория не найдена.", reply_markup=back_keyboard("manage_categories"))
        return

    emoji = category.get("emoji") or ""
    excl = " 🚫 (исключена из бюджета)" if category.get("exclude_from_budget") else ""
    text = f"Категория: {emoji} {category['name']}{excl}"

    await query.edit_message_text(
        text,
        reply_markup=category_actions_keyboard(category_id, bool(category.get("exclude_from_budget")))
    )


@auth_callback
async def cat_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления категории."""
    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "cat_add_name"
    await query.edit_message_text(
        "➕ Введите название новой категории:\n"
        "Можно добавить эмодзи в начале, например: <code>🍕 Пицца</code>",
        parse_mode="HTML"
    )


async def cat_add_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода названия новой категории."""
    state = context.user_data.get("state")
    if state != "cat_add_name":
        return

    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("❌ Название не может быть пустым.")
        return

    # Пробуем извлечь эмодзи из начала строки
    parts = text.split(None, 1)
    emoji = None
    name = text

    if len(parts) == 2:
        # Проверяем, является ли первое слово эмодзи (простая эвристика)
        first = parts[0]
        if len(first) <= 4 and not first.isalpha():
            emoji = first
            name = parts[1]

    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        await queries.add_category(db, group_id, name, emoji)

    context.user_data.pop("state", None)

    prefix = f"{emoji} " if emoji else ""
    await update.message.reply_text(
        f"✅ Категория «{prefix}{name}» добавлена.",
        reply_markup=management_keyboard()
    )


@auth_callback
async def cat_rename_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало переименования категории."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[2])
    context.user_data["state"] = "cat_rename_input"
    context.user_data["rename_cat_id"] = category_id

    await query.edit_message_text("✏️ Введите новое название категории:")


async def cat_rename_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода нового названия."""
    state = context.user_data.get("state")
    if state != "cat_rename_input":
        return

    new_name = update.message.text.strip()
    if not new_name:
        await update.message.reply_text("❌ Название не может быть пустым.")
        return

    category_id = context.user_data.get("rename_cat_id")
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        await queries.rename_category(db, category_id, group_id, new_name)

    context.user_data.pop("state", None)
    context.user_data.pop("rename_cat_id", None)

    await update.message.reply_text(
        f"✅ Категория переименована в «{new_name}».",
        reply_markup=management_keyboard()
    )


@auth_callback
async def cat_toggle_exclusion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переключить исключение категории из бюджета."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[3])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        new_value = await queries.toggle_category_budget_exclusion(db, category_id, group_id)

    if new_value is None:
        await query.edit_message_text("Категория не найдена.", reply_markup=back_keyboard("manage_categories"))
        return

    status = "исключена из бюджета 🚫" if new_value else "включена в бюджет ✅"
    await query.edit_message_text(
        f"Категория {status}.",
        reply_markup=back_keyboard("manage_categories")
    )


@auth_callback
async def cat_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления категории."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[2])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        count = await queries.get_expenses_count_by_category(db, category_id, group_id)

    context.user_data["delete_cat_id"] = category_id
    warning = f"\n\n⚠️ В категории {count} трат — они будут отвязаны." if count > 0 else ""

    await query.edit_message_text(
        f"Удалить категорию?{warning}",
        reply_markup=confirm_delete_keyboard(
            f"cat_delete_yes_{category_id}",
            "manage_categories"
        )
    )


@auth_callback
async def cat_delete_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление категории подтверждено."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[3])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        await queries.delete_category(db, category_id, group_id)

    await query.edit_message_text("✅ Категория удалена.", reply_markup=management_keyboard())


# ==================== Редактирование трат ====================

@auth_callback
async def manage_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список последних трат для редактирования."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        expenses = await queries.get_last_expenses(db, group_id, limit=10)

    if not expenses:
        await query.edit_message_text("Трат пока нет.", reply_markup=back_keyboard("management"))
        return

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for exp in expenses:
        emoji = exp.get("category_emoji") or ""
        cat = exp.get("category_name") or "?"
        amount = format_amount(float(exp["amount"]))
        date = format_date(str(exp["created_at"])[:10])
        label = f"{emoji} {cat} — {amount} ₽ ({date})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"editexp_{exp['id']}")])

    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="management")])
    await query.edit_message_text(
        "✏️ Выберите трату для редактирования:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@auth_callback
async def expense_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Действия с тратой."""
    query = update.callback_query
    await query.answer()

    expense_id = int(query.data.split("_")[1])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        expense = await queries.get_expense_by_id(db, expense_id, group_id)

    if not expense:
        await query.edit_message_text("Трата не найдена.", reply_markup=back_keyboard("manage_expenses"))
        return

    emoji = expense.get("category_emoji") or ""
    cat = expense.get("category_name") or "?"
    amount = format_amount(float(expense["amount"]))
    date = format_date(str(expense["created_at"])[:10])
    comment = f"\n💬 {expense['comment']}" if expense.get("comment") else ""
    user = expense.get("user_name") or "?"

    text = f"{emoji} {cat} — {amount} ₽\n👤 {user}  📅 {date}{comment}"
    await query.edit_message_text(text, reply_markup=expense_actions_keyboard(expense_id))


@auth_callback
async def edit_amount_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования суммы."""
    query = update.callback_query
    await query.answer()

    expense_id = int(query.data.split("_")[2])
    context.user_data["state"] = "edit_amount"
    context.user_data["edit_expense_id"] = expense_id
    await query.edit_message_text("💰 Введите новую сумму:")


async def edit_amount_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка новой суммы."""
    if context.user_data.get("state") != "edit_amount":
        return

    text = update.message.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введите корректную сумму.")
        return

    expense_id = context.user_data.get("edit_expense_id")
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        await queries.update_expense_amount(db, expense_id, group_id, amount)

    context.user_data.pop("state", None)
    context.user_data.pop("edit_expense_id", None)

    await update.message.reply_text(
        f"✅ Сумма обновлена: {format_amount(amount)} ₽",
        reply_markup=management_keyboard()
    )


@auth_callback
async def edit_cat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало смены категории траты."""
    query = update.callback_query
    await query.answer()

    expense_id = int(query.data.split("_")[2])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        categories = await queries.get_all_categories(db, group_id)

    context.user_data["edit_expense_id"] = expense_id
    context.user_data["state"] = "edit_cat_select"

    await query.edit_message_text(
        "🗂 Выберите новую категорию:",
        reply_markup=categories_keyboard(categories, callback_prefix="editcatsel")
    )


@auth_callback
async def edit_cat_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Новая категория выбрана."""
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    expense_id = context.user_data.get("edit_expense_id")
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        await queries.update_expense_category(db, expense_id, group_id, category_id)

    context.user_data.pop("state", None)
    context.user_data.pop("edit_expense_id", None)

    await query.edit_message_text("✅ Категория обновлена.", reply_markup=management_keyboard())


@auth_callback
async def edit_comment_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования комментария."""
    query = update.callback_query
    await query.answer()

    expense_id = int(query.data.split("_")[2])
    context.user_data["state"] = "edit_comment"
    context.user_data["edit_expense_id"] = expense_id
    await query.edit_message_text("💬 Введите новый комментарий:")


async def edit_comment_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового комментария."""
    if context.user_data.get("state") != "edit_comment":
        return

    comment = update.message.text.strip()
    expense_id = context.user_data.get("edit_expense_id")
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        await queries.update_expense_comment(db, expense_id, group_id, comment)

    context.user_data.pop("state", None)
    context.user_data.pop("edit_expense_id", None)

    await update.message.reply_text("✅ Комментарий обновлён.", reply_markup=management_keyboard())


@auth_callback
async def delete_expense_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления траты."""
    query = update.callback_query
    await query.answer()

    expense_id = int(query.data.split("_")[2])
    await query.edit_message_text(
        "Удалить эту трату?",
        reply_markup=confirm_delete_keyboard(
            f"delete_expense_yes_{expense_id}",
            f"editexp_{expense_id}"
        )
    )


@auth_callback
async def delete_expense_yes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление траты подтверждено."""
    query = update.callback_query
    await query.answer()

    expense_id = int(query.data.split("_")[3])
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        await queries.delete_expense(db, expense_id, group_id)

    await query.edit_message_text("✅ Трата удалена.", reply_markup=management_keyboard())


# ==================== Напоминания ====================

@auth_callback
async def manage_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Управление напоминаниями."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        reminder_time = await queries.get_group_reminder_time(db, group_id)

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = [
        [InlineKeyboardButton(f"⏰ Время: {reminder_time}", callback_data="reminder_set_time")],
        [InlineKeyboardButton("◀️ Назад", callback_data="management")],
    ]
    await query.edit_message_text(
        f"🔔 Напоминания\n\nТекущее время: {reminder_time}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@auth_callback
async def reminder_set_time_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало установки времени напоминания."""
    query = update.callback_query
    await query.answer()

    context.user_data["state"] = "reminder_set_time"
    await query.edit_message_text(
        "⏰ Введите время напоминания в формате ЧЧ:ММ\n"
        "Например: <code>22:00</code>",
        parse_mode="HTML"
    )


async def reminder_set_time_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода времени напоминания."""
    if context.user_data.get("state") != "reminder_set_time":
        return

    text = update.message.text.strip()
    parts = text.split(":")
    try:
        if len(parts) != 2:
            raise ValueError
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        time_str = f"{h:02d}:{m:02d}"
    except ValueError:
        await update.message.reply_text("❌ Введите время в формате ЧЧ:ММ, например: <code>22:00</code>", parse_mode="HTML")
        return

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        await queries.set_group_reminder_time(db, group_id, time_str)

    context.user_data.pop("state", None)

    await update.message.reply_text(
        f"✅ Время напоминания установлено: {time_str}",
        reply_markup=management_keyboard()
    )


def get_management_handlers():
    """Получить обработчики для регистрации."""
    return [
        CallbackQueryHandler(management_menu, pattern="^management$"),
        # Категории
        CallbackQueryHandler(manage_categories, pattern="^manage_categories$"),
        CallbackQueryHandler(category_actions, pattern=r"^catmng_\d+$"),
        CallbackQueryHandler(cat_add_start, pattern="^cat_add$"),
        CallbackQueryHandler(cat_rename_start, pattern=r"^cat_rename_\d+$"),
        CallbackQueryHandler(cat_toggle_exclusion, pattern=r"^cat_toggle_excl_\d+$"),
        CallbackQueryHandler(cat_delete_confirm, pattern=r"^cat_delete_\d+$"),
        CallbackQueryHandler(cat_delete_yes, pattern=r"^cat_delete_yes_\d+$"),
        # Траты
        CallbackQueryHandler(manage_expenses, pattern="^manage_expenses$"),
        CallbackQueryHandler(expense_actions, pattern=r"^editexp_\d+$"),
        CallbackQueryHandler(edit_amount_start, pattern=r"^edit_amount_\d+$"),
        CallbackQueryHandler(edit_cat_start, pattern=r"^edit_cat_\d+$"),
        CallbackQueryHandler(edit_cat_selected, pattern=r"^editcatsel_\d+$"),
        CallbackQueryHandler(edit_comment_start, pattern=r"^edit_comment_\d+$"),
        CallbackQueryHandler(delete_expense_confirm, pattern=r"^delete_expense_\d+$"),
        CallbackQueryHandler(delete_expense_yes, pattern=r"^delete_expense_yes_\d+$"),
        # Напоминания
        CallbackQueryHandler(manage_reminders, pattern="^manage_reminders$"),
        CallbackQueryHandler(reminder_set_time_start, pattern="^reminder_set_time$"),
    ]
