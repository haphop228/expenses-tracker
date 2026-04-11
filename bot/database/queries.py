"""
Запросы к PostgreSQL для бота.
Все запросы фильтруются по group_id для мультитенантности.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text


# ==================== ПОЛЬЗОВАТЕЛИ ====================

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[dict]:
    """Получить пользователя по telegram_id."""
    result = await db.execute(
        text("""
            SELECT u.id, u.group_id, u.name, u.role, u.reminder_enabled,
                   g.name as group_name
            FROM users u
            LEFT JOIN groups g ON u.group_id = g.id
            WHERE u.telegram_id = :telegram_id
        """),
        {"telegram_id": telegram_id}
    )
    row = result.mappings().fetchone()
    return dict(row) if row else None


async def update_user_last_seen(db: AsyncSession, user_id: int) -> None:
    """Обновить время последней активности пользователя."""
    await db.execute(
        text("UPDATE users SET last_seen = :now WHERE id = :user_id"),
        {"now": datetime.now(timezone.utc), "user_id": user_id}
    )
    await db.commit()


async def link_telegram_account(
    db: AsyncSession,
    link_code: str,
    telegram_id: int,
    telegram_username: Optional[str] = None,
) -> Optional[dict]:
    """
    Привязать Telegram аккаунт по link_code.
    Возвращает данные пользователя или None если код не найден/истёк.
    """
    # Ищем пользователя с таким link_code
    result = await db.execute(
        text("""
            SELECT id, name, group_id FROM users
            WHERE link_code = :code
              AND link_code_expires > :now
        """),
        {"code": link_code, "now": datetime.now(timezone.utc)}
    )
    row = result.mappings().fetchone()
    if not row:
        return None

    user_id = row["id"]

    # Проверяем что telegram_id не занят другим пользователем
    existing = await db.execute(
        text("SELECT id FROM users WHERE telegram_id = :tid AND id != :uid"),
        {"tid": telegram_id, "uid": user_id}
    )
    if existing.fetchone():
        return None  # telegram_id уже занят

    # Привязываем
    await db.execute(
        text("""
            UPDATE users
            SET telegram_id = :telegram_id,
                telegram_username = :username,
                link_code = NULL,
                link_code_expires = NULL,
                last_seen = :now
            WHERE id = :user_id
        """),
        {
            "telegram_id": telegram_id,
            "username": telegram_username,
            "now": datetime.now(timezone.utc),
            "user_id": user_id,
        }
    )
    await db.commit()
    return dict(row)


# ==================== КАТЕГОРИИ ====================

async def get_all_categories(db: AsyncSession, group_id: int) -> list:
    """Получить все категории группы."""
    result = await db.execute(
        text("""
            SELECT id, name, emoji, exclude_from_budget
            FROM categories
            WHERE group_id = :group_id
            ORDER BY name
        """),
        {"group_id": group_id}
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def get_category_by_id(db: AsyncSession, category_id: int, group_id: int) -> Optional[dict]:
    """Получить категорию по ID (с проверкой group_id)."""
    result = await db.execute(
        text("""
            SELECT id, name, emoji, exclude_from_budget
            FROM categories
            WHERE id = :id AND group_id = :group_id
        """),
        {"id": category_id, "group_id": group_id}
    )
    row = result.mappings().fetchone()
    return dict(row) if row else None


async def add_category(db: AsyncSession, group_id: int, name: str, emoji: Optional[str] = None) -> None:
    """Добавить новую категорию."""
    await db.execute(
        text("""
            INSERT INTO categories (group_id, name, emoji)
            VALUES (:group_id, :name, :emoji)
        """),
        {"group_id": group_id, "name": name, "emoji": emoji}
    )
    await db.commit()


async def rename_category(db: AsyncSession, category_id: int, group_id: int, new_name: str) -> None:
    """Переименовать категорию."""
    await db.execute(
        text("""
            UPDATE categories SET name = :name
            WHERE id = :id AND group_id = :group_id
        """),
        {"name": new_name, "id": category_id, "group_id": group_id}
    )
    await db.commit()


async def delete_category(db: AsyncSession, category_id: int, group_id: int) -> None:
    """Удалить категорию (связанные траты обнуляют category_id через SET NULL)."""
    await db.execute(
        text("""
            DELETE FROM budget_by_category
            WHERE category_id = :id AND group_id = :group_id
        """),
        {"id": category_id, "group_id": group_id}
    )
    await db.execute(
        text("""
            DELETE FROM categories
            WHERE id = :id AND group_id = :group_id
        """),
        {"id": category_id, "group_id": group_id}
    )
    await db.commit()


async def get_categories_count(db: AsyncSession, group_id: int) -> int:
    """Получить количество категорий группы."""
    result = await db.execute(
        text("SELECT COUNT(*) FROM categories WHERE group_id = :group_id"),
        {"group_id": group_id}
    )
    return result.scalar_one()


async def get_expenses_count_by_category(db: AsyncSession, category_id: int, group_id: int) -> int:
    """Получить количество трат в категории."""
    result = await db.execute(
        text("""
            SELECT COUNT(*) FROM expenses
            WHERE category_id = :cat_id AND group_id = :group_id
        """),
        {"cat_id": category_id, "group_id": group_id}
    )
    return result.scalar_one()


async def toggle_category_budget_exclusion(db: AsyncSession, category_id: int, group_id: int) -> Optional[bool]:
    """Переключить исключение категории из бюджета. Возвращает новое значение."""
    result = await db.execute(
        text("""
            SELECT exclude_from_budget FROM categories
            WHERE id = :id AND group_id = :group_id
        """),
        {"id": category_id, "group_id": group_id}
    )
    row = result.fetchone()
    if not row:
        return None
    new_value = not row[0]
    await db.execute(
        text("""
            UPDATE categories SET exclude_from_budget = :val
            WHERE id = :id AND group_id = :group_id
        """),
        {"val": new_value, "id": category_id, "group_id": group_id}
    )
    await db.commit()
    return new_value


# ==================== ТРАТЫ ====================

async def add_expense(
    db: AsyncSession,
    group_id: int,
    user_id: int,
    category_id: int,
    amount: float,
    comment: Optional[str] = None,
    created_at: Optional[str] = None,
) -> None:
    """Добавить трату."""
    if created_at:
        await db.execute(
            text("""
                INSERT INTO expenses (group_id, user_id, category_id, amount, comment, created_at)
                VALUES (:group_id, :user_id, :cat_id, :amount, :comment, :created_at)
            """),
            {
                "group_id": group_id, "user_id": user_id, "cat_id": category_id,
                "amount": amount, "comment": comment, "created_at": created_at,
            }
        )
    else:
        await db.execute(
            text("""
                INSERT INTO expenses (group_id, user_id, category_id, amount, comment)
                VALUES (:group_id, :user_id, :cat_id, :amount, :comment)
            """),
            {
                "group_id": group_id, "user_id": user_id, "cat_id": category_id,
                "amount": amount, "comment": comment,
            }
        )
    await db.commit()


async def get_expense_by_id(db: AsyncSession, expense_id: int, group_id: int) -> Optional[dict]:
    """Получить трату по ID."""
    result = await db.execute(
        text("""
            SELECT e.id, e.user_id, e.category_id, e.amount, e.comment, e.created_at,
                   c.name as category_name, c.emoji as category_emoji,
                   u.name as user_name
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN users u ON e.user_id = u.id
            WHERE e.id = :id AND e.group_id = :group_id
        """),
        {"id": expense_id, "group_id": group_id}
    )
    row = result.mappings().fetchone()
    return dict(row) if row else None


async def get_last_expenses(db: AsyncSession, group_id: int, limit: int = 10) -> list:
    """Получить последние N трат группы."""
    result = await db.execute(
        text("""
            SELECT e.id, e.user_id, e.category_id, e.amount, e.comment, e.created_at,
                   c.name as category_name, c.emoji as category_emoji,
                   u.name as user_name
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN users u ON e.user_id = u.id
            WHERE e.group_id = :group_id
            ORDER BY e.created_at DESC
            LIMIT :limit
        """),
        {"group_id": group_id, "limit": limit}
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def update_expense_amount(db: AsyncSession, expense_id: int, group_id: int, amount: float) -> None:
    """Обновить сумму траты."""
    await db.execute(
        text("UPDATE expenses SET amount = :amount WHERE id = :id AND group_id = :group_id"),
        {"amount": amount, "id": expense_id, "group_id": group_id}
    )
    await db.commit()


async def update_expense_category(db: AsyncSession, expense_id: int, group_id: int, category_id: int) -> None:
    """Обновить категорию траты."""
    await db.execute(
        text("UPDATE expenses SET category_id = :cat_id WHERE id = :id AND group_id = :group_id"),
        {"cat_id": category_id, "id": expense_id, "group_id": group_id}
    )
    await db.commit()


async def update_expense_comment(db: AsyncSession, expense_id: int, group_id: int, comment: str) -> None:
    """Обновить комментарий траты."""
    await db.execute(
        text("UPDATE expenses SET comment = :comment WHERE id = :id AND group_id = :group_id"),
        {"comment": comment, "id": expense_id, "group_id": group_id}
    )
    await db.commit()


async def delete_expense(db: AsyncSession, expense_id: int, group_id: int) -> None:
    """Удалить трату."""
    await db.execute(
        text("DELETE FROM expenses WHERE id = :id AND group_id = :group_id"),
        {"id": expense_id, "group_id": group_id}
    )
    await db.commit()


# ==================== СТАТИСТИКА ====================

async def get_expenses_for_period(db: AsyncSession, group_id: int, date_from: str, date_to: str) -> list:
    """Получить траты за период."""
    result = await db.execute(
        text("""
            SELECT e.id, e.user_id, e.category_id, e.amount, e.comment, e.created_at,
                   c.name as category_name, c.emoji as category_emoji,
                   u.name as user_name
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            LEFT JOIN users u ON e.user_id = u.id
            WHERE e.group_id = :group_id
              AND e.created_at >= :date_from
              AND e.created_at < :date_to
            ORDER BY e.created_at DESC
        """),
        {"group_id": group_id, "date_from": date_from, "date_to": date_to}
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def get_stats_by_category(db: AsyncSession, group_id: int, date_from: str, date_to: str) -> list:
    """Получить статистику по категориям за период."""
    result = await db.execute(
        text("""
            SELECT c.id, c.name, c.emoji,
                   SUM(e.amount) as total,
                   COUNT(e.id) as count
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.group_id = :group_id
              AND e.created_at >= :date_from
              AND e.created_at < :date_to
            GROUP BY c.id, c.name, c.emoji
            ORDER BY total DESC
        """),
        {"group_id": group_id, "date_from": date_from, "date_to": date_to}
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def get_stats_by_user(db: AsyncSession, group_id: int, date_from: str, date_to: str) -> list:
    """Получить статистику по пользователям за период."""
    result = await db.execute(
        text("""
            SELECT e.user_id, u.name as user_name,
                   SUM(e.amount) as total,
                   COUNT(e.id) as count
            FROM expenses e
            LEFT JOIN users u ON e.user_id = u.id
            WHERE e.group_id = :group_id
              AND e.created_at >= :date_from
              AND e.created_at < :date_to
            GROUP BY e.user_id, u.name
            ORDER BY total DESC
        """),
        {"group_id": group_id, "date_from": date_from, "date_to": date_to}
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def get_stats_by_category_budget(
    db: AsyncSession,
    group_id: int,
    date_from: str,
    date_to: str,
    exclude_budget_excluded: bool = False,
) -> list:
    """Статистика по категориям с возможностью исключения."""
    extra = "AND (c.exclude_from_budget = FALSE OR c.exclude_from_budget IS NULL)" if exclude_budget_excluded else ""
    result = await db.execute(
        text(f"""
            SELECT c.id, c.name, c.emoji,
                   SUM(e.amount) as total,
                   COUNT(e.id) as count
            FROM expenses e
            LEFT JOIN categories c ON e.category_id = c.id
            WHERE e.group_id = :group_id
              AND e.created_at >= :date_from
              AND e.created_at < :date_to
              {extra}
            GROUP BY c.id, c.name, c.emoji
            ORDER BY total DESC
        """),
        {"group_id": group_id, "date_from": date_from, "date_to": date_to}
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def get_all_expenses_for_export(
    db: AsyncSession,
    group_id: int,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> list:
    """Получить все траты для экспорта в Excel."""
    if date_from and date_to:
        result = await db.execute(
            text("""
                SELECT e.created_at, u.name as user_name,
                       c.name as category_name, c.emoji,
                       e.amount, e.comment
                FROM expenses e
                LEFT JOIN categories c ON e.category_id = c.id
                LEFT JOIN users u ON e.user_id = u.id
                WHERE e.group_id = :group_id
                  AND e.created_at >= :date_from
                  AND e.created_at < :date_to
                ORDER BY e.created_at DESC
            """),
            {"group_id": group_id, "date_from": date_from, "date_to": date_to}
        )
    else:
        result = await db.execute(
            text("""
                SELECT e.created_at, u.name as user_name,
                       c.name as category_name, c.emoji,
                       e.amount, e.comment
                FROM expenses e
                LEFT JOIN categories c ON e.category_id = c.id
                LEFT JOIN users u ON e.user_id = u.id
                WHERE e.group_id = :group_id
                ORDER BY e.created_at DESC
            """),
            {"group_id": group_id}
        )
    return [dict(row) for row in result.mappings().fetchall()]


# ==================== БЮДЖЕТ ====================

async def get_budget(db: AsyncSession, group_id: int, month: str) -> Optional[float]:
    """Получить бюджет на месяц."""
    result = await db.execute(
        text("SELECT amount FROM budget WHERE group_id = :group_id AND month = :month"),
        {"group_id": group_id, "month": month}
    )
    row = result.fetchone()
    return float(row[0]) if row else None


async def set_budget(db: AsyncSession, group_id: int, month: str, amount: float) -> None:
    """Установить бюджет на месяц."""
    existing = await get_budget(db, group_id, month)
    if existing is not None:
        await db.execute(
            text("UPDATE budget SET amount = :amount WHERE group_id = :group_id AND month = :month"),
            {"amount": amount, "group_id": group_id, "month": month}
        )
    else:
        await db.execute(
            text("INSERT INTO budget (group_id, month, amount) VALUES (:group_id, :month, :amount)"),
            {"group_id": group_id, "month": month, "amount": amount}
        )
    await db.commit()


async def get_budget_by_category(db: AsyncSession, group_id: int, month: str) -> list:
    """Получить бюджет по категориям на месяц."""
    result = await db.execute(
        text("""
            SELECT bc.category_id, bc.amount, c.name, c.emoji
            FROM budget_by_category bc
            LEFT JOIN categories c ON bc.category_id = c.id
            WHERE bc.group_id = :group_id AND bc.month = :month
        """),
        {"group_id": group_id, "month": month}
    )
    return [dict(row) for row in result.mappings().fetchall()]


async def set_budget_for_category(
    db: AsyncSession,
    group_id: int,
    month: str,
    category_id: int,
    amount: float,
) -> None:
    """Установить бюджет для категории на месяц."""
    result = await db.execute(
        text("""
            SELECT id FROM budget_by_category
            WHERE group_id = :group_id AND month = :month AND category_id = :cat_id
        """),
        {"group_id": group_id, "month": month, "cat_id": category_id}
    )
    existing = result.fetchone()
    if existing:
        await db.execute(
            text("""
                UPDATE budget_by_category SET amount = :amount
                WHERE group_id = :group_id AND month = :month AND category_id = :cat_id
            """),
            {"amount": amount, "group_id": group_id, "month": month, "cat_id": category_id}
        )
    else:
        await db.execute(
            text("""
                INSERT INTO budget_by_category (group_id, month, category_id, amount)
                VALUES (:group_id, :month, :cat_id, :amount)
            """),
            {"group_id": group_id, "month": month, "cat_id": category_id, "amount": amount}
        )
    await db.commit()


async def get_total_spent_for_month(
    db: AsyncSession,
    group_id: int,
    month: str,
    exclude_budget_excluded: bool = False,
) -> float:
    """Получить общую сумму трат за месяц."""
    year, mon = map(int, month.split("-"))
    date_from = f"{month}-01"
    if mon == 12:
        next_month = f"{year + 1}-01-01"
    else:
        next_month = f"{year}-{mon + 1:02d}-01"

    if exclude_budget_excluded:
        result = await db.execute(
            text("""
                SELECT COALESCE(SUM(e.amount), 0)
                FROM expenses e
                JOIN categories c ON e.category_id = c.id
                WHERE e.group_id = :group_id
                  AND e.created_at >= :date_from
                  AND e.created_at < :next_month
                  AND c.exclude_from_budget = FALSE
            """),
            {"group_id": group_id, "date_from": date_from, "next_month": next_month}
        )
    else:
        result = await db.execute(
            text("""
                SELECT COALESCE(SUM(amount), 0)
                FROM expenses
                WHERE group_id = :group_id
                  AND created_at >= :date_from
                  AND created_at < :next_month
            """),
            {"group_id": group_id, "date_from": date_from, "next_month": next_month}
        )
    return float(result.scalar_one() or 0.0)


# ==================== НАСТРОЙКИ ГРУППЫ ====================

# Whitelist допустимых полей настроек — защита от SQL Injection
_ALLOWED_SETTING_KEYS = frozenset({
    "reminder_time", "timezone", "currency",
    "reminder_enabled", "language",
})


async def get_group_setting(db: AsyncSession, group_id: int, key: str) -> Optional[str]:
    """Получить настройку группы."""
    if key not in _ALLOWED_SETTING_KEYS:
        raise ValueError(f"Недопустимое поле настройки: {key!r}")
    # Имя колонки безопасно — проверено whitelist'ом выше
    result = await db.execute(
        text(f"SELECT {key} FROM group_settings WHERE group_id = :group_id"),
        {"group_id": group_id}
    )
    row = result.fetchone()
    return str(row[0]) if row and row[0] is not None else None


async def get_group_reminder_time(db: AsyncSession, group_id: int) -> str:
    """Получить время напоминания для группы."""
    result = await db.execute(
        text("SELECT reminder_time FROM group_settings WHERE group_id = :group_id"),
        {"group_id": group_id}
    )
    row = result.fetchone()
    return row[0] if row else "22:00"


async def set_group_reminder_time(db: AsyncSession, group_id: int, time_str: str) -> None:
    """Установить время напоминания для группы."""
    result = await db.execute(
        text("SELECT group_id FROM group_settings WHERE group_id = :group_id"),
        {"group_id": group_id}
    )
    if result.fetchone():
        await db.execute(
            text("UPDATE group_settings SET reminder_time = :time WHERE group_id = :group_id"),
            {"time": time_str, "group_id": group_id}
        )
    else:
        await db.execute(
            text("INSERT INTO group_settings (group_id, reminder_time) VALUES (:group_id, :time)"),
            {"group_id": group_id, "time": time_str}
        )
    await db.commit()


async def get_all_groups_with_reminders(db: AsyncSession) -> list:
    """Получить все группы с настройками напоминаний и telegram_id участников."""
    result = await db.execute(
        text("""
            SELECT g.id as group_id, g.name as group_name,
                   gs.reminder_time, gs.timezone,
                   u.telegram_id, u.name as user_name, u.reminder_enabled
            FROM groups g
            JOIN group_settings gs ON g.id = gs.group_id
            JOIN users u ON u.group_id = g.id
            WHERE u.telegram_id IS NOT NULL
              AND u.reminder_enabled = TRUE
        """)
    )
    return [dict(row) for row in result.mappings().fetchall()]
