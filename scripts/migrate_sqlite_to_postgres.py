#!/usr/bin/env python3
"""
Скрипт миграции данных из SQLite в PostgreSQL.

Переносит данные существующего бота (expenses.db) в новую
мультитенантную PostgreSQL базу данных.

Использование:
    python migrate_sqlite_to_postgres.py \
        --sqlite-path /path/to/expenses.db \
        --group-name "Семья Ивановых" \
        --postgres-url "postgresql://user:pass@localhost:5432/expenses"

Опционально (для указания ролей):
    --admin-telegram-ids 123456789,987654321
"""

import asyncio
import argparse
import sqlite3
import sys
from datetime import datetime, timezone

try:
    import asyncpg
except ImportError:
    print("❌ Установите asyncpg: pip install asyncpg")
    sys.exit(1)


DEFAULT_CATEGORIES = [
    {"name": "Продукты", "emoji": "🛒"},
    {"name": "Кафе", "emoji": "☕"},
    {"name": "Транспорт", "emoji": "🚕"},
    {"name": "Аптека", "emoji": "💊"},
    {"name": "Досуг", "emoji": "🎮"},
    {"name": "Одежда", "emoji": "👗"},
    {"name": "Дом", "emoji": "🏠"},
    {"name": "Прочее", "emoji": "📦"},
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Миграция данных из SQLite в PostgreSQL"
    )
    parser.add_argument(
        "--sqlite-path",
        required=True,
        help="Путь к SQLite файлу (expenses.db)"
    )
    parser.add_argument(
        "--group-name",
        required=True,
        help="Название группы в новой системе"
    )
    parser.add_argument(
        "--postgres-url",
        required=True,
        help="PostgreSQL connection URL (postgresql://user:pass@host:5432/db)"
    )
    parser.add_argument(
        "--admin-telegram-ids",
        default="",
        help="Telegram ID пользователей с ролью admin (через запятую)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Только показать что будет перенесено, без записи в БД"
    )
    return parser.parse_args()


def read_sqlite(sqlite_path: str) -> dict:
    """Читает все данные из SQLite."""
    print(f"\n📂 Читаю SQLite: {sqlite_path}")

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row

    data = {}

    # Категории
    cursor = conn.execute("SELECT * FROM categories ORDER BY id")
    data["categories"] = [dict(row) for row in cursor.fetchall()]
    print(f"   Категорий: {len(data['categories'])}")

    # Траты
    cursor = conn.execute("SELECT * FROM expenses ORDER BY created_at")
    data["expenses"] = [dict(row) for row in cursor.fetchall()]
    print(f"   Трат: {len(data['expenses'])}")

    # Бюджет
    cursor = conn.execute("SELECT * FROM budget ORDER BY month")
    data["budget"] = [dict(row) for row in cursor.fetchall()]
    print(f"   Записей бюджета: {len(data['budget'])}")

    # Бюджет по категориям
    cursor = conn.execute("SELECT * FROM budget_by_category ORDER BY month, category_id")
    data["budget_by_category"] = [dict(row) for row in cursor.fetchall()]
    print(f"   Лимитов по категориям: {len(data['budget_by_category'])}")

    # Уникальные user_id из трат
    cursor = conn.execute("SELECT DISTINCT user_id FROM expenses ORDER BY user_id")
    data["user_ids"] = [row[0] for row in cursor.fetchall()]
    print(f"   Уникальных пользователей в тратах: {len(data['user_ids'])}")

    conn.close()
    return data


async def migrate(args):
    """Основная функция миграции."""
    # Читаем SQLite
    sqlite_data = read_sqlite(args.sqlite_path)

    # Парсим admin IDs
    admin_ids = set()
    if args.admin_telegram_ids:
        for tid in args.admin_telegram_ids.split(","):
            tid = tid.strip()
            if tid:
                admin_ids.add(int(tid))

    if args.dry_run:
        print("\n🔍 DRY RUN — данные не будут записаны в PostgreSQL")
        print(f"\n📋 Будет создано:")
        print(f"   Группа: '{args.group_name}'")
        print(f"   Пользователей: {len(sqlite_data['user_ids'])}")
        print(f"   Категорий: {len(sqlite_data['categories'])}")
        print(f"   Трат: {len(sqlite_data['expenses'])}")
        print(f"   Записей бюджета: {len(sqlite_data['budget'])}")
        print(f"   Лимитов по категориям: {len(sqlite_data['budget_by_category'])}")
        return

    print(f"\n🔌 Подключаюсь к PostgreSQL...")
    conn = await asyncpg.connect(args.postgres_url)

    try:
        async with conn.transaction():
            # ==================== 1. Создать группу ====================
            group_id = await conn.fetchval(
                """
                INSERT INTO groups (name)
                VALUES ($1)
                RETURNING id
                """,
                args.group_name
            )
            print(f"\n✅ Создана группа '{args.group_name}' (id: {group_id})")

            # Создать настройки группы
            await conn.execute(
                """
                INSERT INTO group_settings (group_id, reminder_time, timezone, currency)
                VALUES ($1, '22:00', 'Europe/Moscow', '₽')
                """,
                group_id
            )

            # ==================== 2. Создать пользователей ====================
            # Маппинг: старый telegram_id -> новый user_id в PostgreSQL
            users_map: dict[int, int] = {}

            for telegram_id in sqlite_data["user_ids"]:
                role = "admin" if telegram_id in admin_ids else "member"
                user_id = await conn.fetchval(
                    """
                    INSERT INTO users (group_id, name, telegram_id, role)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    group_id,
                    f"Пользователь {telegram_id}",  # Имя можно обновить позже
                    telegram_id,
                    role
                )
                users_map[telegram_id] = user_id

            print(f"✅ Создано пользователей: {len(users_map)}")

            # ==================== 3. Перенести категории ====================
            # Маппинг: старый category_id -> новый category_id в PostgreSQL
            categories_map: dict[int, int] = {}

            for cat in sqlite_data["categories"]:
                exclude = bool(cat.get("exclude_from_budget", 0))
                new_cat_id = await conn.fetchval(
                    """
                    INSERT INTO categories (group_id, name, emoji, exclude_from_budget)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (group_id, name) DO UPDATE
                        SET emoji = EXCLUDED.emoji,
                            exclude_from_budget = EXCLUDED.exclude_from_budget
                    RETURNING id
                    """,
                    group_id,
                    cat["name"],
                    cat.get("emoji"),
                    exclude
                )
                categories_map[cat["id"]] = new_cat_id

            print(f"✅ Перенесено категорий: {len(categories_map)}")

            # ==================== 4. Перенести траты ====================
            expenses_count = 0
            expenses_skipped = 0

            for exp in sqlite_data["expenses"]:
                new_user_id = users_map.get(exp["user_id"])
                new_cat_id = categories_map.get(exp["category_id"])

                if new_user_id is None:
                    expenses_skipped += 1
                    continue

                # Парсим дату из SQLite (может быть строкой)
                created_at = exp.get("created_at")
                if isinstance(created_at, str):
                    # SQLite хранит как "2024-11-14 14:23:00" или "2024-11-14T14:23:00"
                    created_at = created_at.replace("T", " ")
                    try:
                        created_at = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    except ValueError:
                        created_at = datetime.now(timezone.utc)

                await conn.execute(
                    """
                    INSERT INTO expenses (group_id, user_id, category_id, amount, comment, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """,
                    group_id,
                    new_user_id,
                    new_cat_id,
                    float(exp["amount"]),
                    exp.get("comment"),
                    created_at
                )
                expenses_count += 1

            print(f"✅ Перенесено трат: {expenses_count}")
            if expenses_skipped:
                print(f"⚠️  Пропущено трат (неизвестный user_id): {expenses_skipped}")

            # ==================== 5. Перенести бюджет ====================
            budget_count = 0

            for b in sqlite_data["budget"]:
                await conn.execute(
                    """
                    INSERT INTO budget (group_id, month, amount)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (group_id, month) DO UPDATE SET amount = EXCLUDED.amount
                    """,
                    group_id,
                    b["month"],
                    float(b["amount"])
                )
                budget_count += 1

            print(f"✅ Перенесено записей бюджета: {budget_count}")

            # ==================== 6. Перенести лимиты по категориям ====================
            budget_cat_count = 0

            for bc in sqlite_data["budget_by_category"]:
                new_cat_id = categories_map.get(bc["category_id"])
                if new_cat_id is None:
                    continue

                await conn.execute(
                    """
                    INSERT INTO budget_by_category (group_id, month, category_id, amount)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (group_id, month, category_id) DO UPDATE SET amount = EXCLUDED.amount
                    """,
                    group_id,
                    bc["month"],
                    new_cat_id,
                    float(bc["amount"])
                )
                budget_cat_count += 1

            print(f"✅ Перенесено лимитов по категориям: {budget_cat_count}")

        # ==================== Итог ====================
        print("\n" + "=" * 55)
        print("✅ Миграция завершена успешно!")
        print("=" * 55)
        print(f"\n📊 Итоги:")
        print(f"   Группа:                  '{args.group_name}' (id: {group_id})")
        print(f"   Пользователей:           {len(users_map)}")
        print(f"   Категорий:               {len(categories_map)}")
        print(f"   Трат:                    {expenses_count}")
        print(f"   Записей бюджета:         {budget_count}")
        print(f"   Лимитов по категориям:   {budget_cat_count}")

        if admin_ids:
            print(f"\n👑 Администраторы группы (telegram_id): {', '.join(str(i) for i in admin_ids)}")

        print(f"""
⚠️  Следующие шаги:
   1. Обновите имена пользователей в таблице users (сейчас "Пользователь <id>")
   2. Запустите бота — пользователи смогут привязать Telegram через /link
   3. Зарегистрируйтесь на сайте через инвайт-ссылку
""")

    except Exception as e:
        print(f"\n❌ Ошибка миграции: {e}")
        raise
    finally:
        await conn.close()


def main():
    args = parse_args()

    # Проверяем что SQLite файл существует
    import os
    if not os.path.exists(args.sqlite_path):
        print(f"❌ SQLite файл не найден: {args.sqlite_path}")
        sys.exit(1)

    print("🚀 Запуск миграции SQLite → PostgreSQL")
    print(f"   SQLite:     {args.sqlite_path}")
    print(f"   Группа:     {args.group_name}")
    print(f"   PostgreSQL: {args.postgres_url.split('@')[-1]}")  # Скрываем пароль

    asyncio.run(migrate(args))


if __name__ == "__main__":
    main()
