from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню."""
    buttons = [
        [InlineKeyboardButton("💸 Добавить трату", callback_data="add_expense")],
        [
            InlineKeyboardButton("📊 Статистика", callback_data="statistics"),
            InlineKeyboardButton("💰 Бюджет", callback_data="budget"),
        ],
        [InlineKeyboardButton("⚙️ Управление", callback_data="management")],
    ]
    return InlineKeyboardMarkup(buttons)


def categories_keyboard(categories: list, callback_prefix: str = "cat") -> InlineKeyboardMarkup:
    """Клавиатура выбора категории."""
    buttons = []
    for cat in categories:
        emoji = cat.get("emoji") or ""
        label = f"{emoji} {cat['name']}" if emoji else cat["name"]
        buttons.append([InlineKeyboardButton(label, callback_data=f"{callback_prefix}_{cat['id']}")])
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def confirm_expense_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения траты."""
    buttons = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_expense"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_expense"),
        ],
        [InlineKeyboardButton("📅 Изменить дату", callback_data="set_expense_date")],
    ]
    return InlineKeyboardMarkup(buttons)


def statistics_keyboard() -> InlineKeyboardMarkup:
    """Меню статистики."""
    buttons = [
        [InlineKeyboardButton("📅 Текущий месяц", callback_data="stats_month")],
        [InlineKeyboardButton("📆 Прошлый месяц", callback_data="stats_prev_month")],
        [InlineKeyboardButton("📋 Последние траты", callback_data="stats_last")],
        [InlineKeyboardButton("📥 Экспорт в Excel", callback_data="stats_export")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(buttons)


def budget_keyboard() -> InlineKeyboardMarkup:
    """Меню бюджета."""
    buttons = [
        [InlineKeyboardButton("📊 Текущий бюджет", callback_data="budget_view")],
        [InlineKeyboardButton("✏️ Установить бюджет", callback_data="budget_set")],
        [InlineKeyboardButton("🗂 Лимиты по категориям", callback_data="budget_categories")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(buttons)


def management_keyboard() -> InlineKeyboardMarkup:
    """Меню управления."""
    buttons = [
        [InlineKeyboardButton("📋 Категории", callback_data="manage_categories")],
        [InlineKeyboardButton("✏️ Редактировать траты", callback_data="manage_expenses")],
        [InlineKeyboardButton("🔔 Напоминания", callback_data="manage_reminders")],
        [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(buttons)


def categories_manage_keyboard(categories: list) -> InlineKeyboardMarkup:
    """Клавиатура управления категориями."""
    buttons = []
    for cat in categories:
        emoji = cat.get("emoji") or ""
        excluded = " 🚫" if cat.get("exclude_from_budget") else ""
        label = f"{emoji} {cat['name']}{excluded}" if emoji else f"{cat['name']}{excluded}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"catmng_{cat['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")])
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="management")])
    return InlineKeyboardMarkup(buttons)


def category_actions_keyboard(category_id: int, exclude_from_budget: bool) -> InlineKeyboardMarkup:
    """Действия с категорией."""
    excl_label = "✅ Включить в бюджет" if exclude_from_budget else "🚫 Исключить из бюджета"
    buttons = [
        [InlineKeyboardButton("✏️ Переименовать", callback_data=f"cat_rename_{category_id}")],
        [InlineKeyboardButton(excl_label, callback_data=f"cat_toggle_excl_{category_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"cat_delete_{category_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="manage_categories")],
    ]
    return InlineKeyboardMarkup(buttons)


def expense_actions_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Действия с тратой."""
    buttons = [
        [InlineKeyboardButton("💰 Изменить сумму", callback_data=f"edit_amount_{expense_id}")],
        [InlineKeyboardButton("🗂 Изменить категорию", callback_data=f"edit_cat_{expense_id}")],
        [InlineKeyboardButton("💬 Изменить комментарий", callback_data=f"edit_comment_{expense_id}")],
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_expense_{expense_id}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="manage_expenses")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_keyboard(callback: str = "back_main") -> InlineKeyboardMarkup:
    """Простая кнопка назад."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data=callback)]])


def confirm_delete_keyboard(callback_yes: str, callback_no: str) -> InlineKeyboardMarkup:
    """Подтверждение удаления."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=callback_yes),
            InlineKeyboardButton("❌ Нет", callback_data=callback_no),
        ]
    ])
