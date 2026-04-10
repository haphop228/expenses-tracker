import calendar
import io
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from handlers.auth import auth_callback
from database.db import AsyncSessionLocal
from database import queries
from keyboards.keyboards import statistics_keyboard, back_keyboard, main_menu_keyboard
from utils.formatters import format_amount, format_date


def _get_month_bounds(year: int, mon: int):
    """Вернуть (date_from, date_to) для месяца."""
    last_day = calendar.monthrange(year, mon)[1]
    date_from = f"{year}-{mon:02d}-01"
    date_to = f"{year}-{mon:02d}-{last_day} 23:59:59"
    return date_from, date_to


def _format_stats_text(title: str, by_cat: list, by_user: list) -> str:
    """Форматировать текст статистики."""
    total = sum(row["total"] for row in by_cat if row["total"])
    lines = [f"📊 {title}\n"]
    lines.append(f"💰 Итого: <b>{format_amount(total)} ₽</b>\n")

    if by_cat:
        lines.append("По категориям:")
        for row in by_cat:
            emoji = row.get("emoji") or ""
            name = row.get("name") or "Без категории"
            pct = (row["total"] / total * 100) if total > 0 else 0
            lines.append(f"  {emoji} {name}: {format_amount(row['total'])} ₽ ({pct:.0f}%)")
    else:
        lines.append("Трат за этот период нет.")

    if by_user:
        lines.append("\nПо участникам:")
        for row in by_user:
            name = row.get("user_name") or f"User #{row['user_id']}"
            lines.append(f"  👤 {name}: {format_amount(row['total'])} ₽")

    return "\n".join(lines)


@auth_callback
async def statistics_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Меню статистики."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📊 Статистика:", reply_markup=statistics_keyboard())


@auth_callback
async def stats_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика за сегодня."""
    query = update.callback_query
    await query.answer()

    now = datetime.now()
    date_from = now.strftime("%Y-%m-%d")
    date_to = now.strftime("%Y-%m-%d 23:59:59")
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        by_cat = await queries.get_stats_by_category(db, group_id, date_from, date_to)
        by_user = await queries.get_stats_by_user(db, group_id, date_from, date_to)

    title = f"Сегодня, {now.strftime('%d.%m.%Y')}"
    text = _format_stats_text(title, by_cat, by_user)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_keyboard("statistics"))


@auth_callback
async def stats_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика за последние 7 дней."""
    query = update.callback_query
    await query.answer()

    now = datetime.now()
    week_ago = now - timedelta(days=6)
    date_from = week_ago.strftime("%Y-%m-%d")
    date_to = now.strftime("%Y-%m-%d 23:59:59")
    group_id = context.user_data["group_id"]

    async with AsyncSessionLocal() as db:
        by_cat = await queries.get_stats_by_category(db, group_id, date_from, date_to)
        by_user = await queries.get_stats_by_user(db, group_id, date_from, date_to)

    title = f"Неделя ({week_ago.strftime('%d.%m')}–{now.strftime('%d.%m.%Y')})"
    text = _format_stats_text(title, by_cat, by_user)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_keyboard("statistics"))


@auth_callback
async def stats_current_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика за текущий месяц."""
    query = update.callback_query
    await query.answer()

    now = datetime.now()
    group_id = context.user_data["group_id"]
    date_from, date_to = _get_month_bounds(now.year, now.month)

    async with AsyncSessionLocal() as db:
        by_cat = await queries.get_stats_by_category(db, group_id, date_from, date_to)
        by_user = await queries.get_stats_by_user(db, group_id, date_from, date_to)

    title = f"Текущий месяц ({now.strftime('%B %Y')})"
    text = _format_stats_text(title, by_cat, by_user)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_keyboard("statistics"))


@auth_callback
async def stats_prev_month(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статистика за прошлый месяц."""
    query = update.callback_query
    await query.answer()

    now = datetime.now()
    if now.month == 1:
        year, mon = now.year - 1, 12
    else:
        year, mon = now.year, now.month - 1

    group_id = context.user_data["group_id"]
    date_from, date_to = _get_month_bounds(year, mon)

    async with AsyncSessionLocal() as db:
        by_cat = await queries.get_stats_by_category(db, group_id, date_from, date_to)
        by_user = await queries.get_stats_by_user(db, group_id, date_from, date_to)

    month_name = datetime(year, mon, 1).strftime("%B %Y")
    title = f"Прошлый месяц ({month_name})"
    text = _format_stats_text(title, by_cat, by_user)
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=back_keyboard("statistics"))


@auth_callback
async def stats_last_expenses(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последние 10 трат."""
    query = update.callback_query
    await query.answer()

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        expenses = await queries.get_last_expenses(db, group_id, limit=10)

    if not expenses:
        await query.edit_message_text(
            "Трат пока нет.",
            reply_markup=back_keyboard("statistics")
        )
        return

    lines = ["📋 Последние траты:\n"]
    for exp in expenses:
        emoji = exp.get("category_emoji") or ""
        cat = exp.get("category_name") or "Без категории"
        amount = format_amount(float(exp["amount"]))
        date = format_date(str(exp["created_at"])[:10])
        user = exp.get("user_name") or "?"
        comment = f" — {exp['comment']}" if exp.get("comment") else ""
        lines.append(f"{emoji} {cat}: <b>{amount} ₽</b>{comment}")
        lines.append(f"   👤 {user}  📅 {date}")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=back_keyboard("statistics")
    )


@auth_callback
async def stats_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт трат в Excel."""
    query = update.callback_query
    await query.answer("Подготовка файла...")

    group_id = context.user_data["group_id"]
    async with AsyncSessionLocal() as db:
        expenses = await queries.get_all_expenses_for_export(db, group_id)

    if not expenses:
        await query.edit_message_text("Трат для экспорта нет.", reply_markup=back_keyboard("statistics"))
        return

    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Траты"
        ws.append(["Дата", "Пользователь", "Категория", "Сумма", "Комментарий"])

        for exp in expenses:
            ws.append([
                str(exp.get("created_at", ""))[:16],
                exp.get("user_name") or "",
                f"{exp.get('emoji', '')} {exp.get('category_name', '')}".strip(),
                float(exp.get("amount", 0)),
                exp.get("comment") or "",
            ])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        filename = f"expenses_{datetime.now().strftime('%Y%m%d')}.xlsx"
        await query.message.reply_document(
            document=buf,
            filename=filename,
            caption="📥 Экспорт трат",
        )
        await query.edit_message_text("✅ Файл отправлен.", reply_markup=back_keyboard("statistics"))
    except Exception as e:
        await query.edit_message_text(
            f"❌ Ошибка при создании файла: {e}",
            reply_markup=back_keyboard("statistics")
        )


def get_statistics_handlers():
    """Получить обработчики для регистрации."""
    return [
        CallbackQueryHandler(statistics_menu, pattern="^statistics$"),
        CallbackQueryHandler(stats_today, pattern="^stats_today$"),
        CallbackQueryHandler(stats_week, pattern="^stats_week$"),
        CallbackQueryHandler(stats_current_month, pattern="^stats_month$"),
        CallbackQueryHandler(stats_prev_month, pattern="^stats_prev_month$"),
        CallbackQueryHandler(stats_last_expenses, pattern="^stats_last$"),
        CallbackQueryHandler(stats_export, pattern="^stats_export$"),
    ]
