"""
Планировщик напоминаний для бота.
Отправляет ежедневные напоминания участникам групп.
"""
import logging
from datetime import datetime

import pytz
from telegram import Bot
from telegram.ext import Application

from database.db import AsyncSessionLocal
from database import queries

logger = logging.getLogger(__name__)

_scheduler = None


async def send_reminders(bot: Bot) -> None:
    """Отправить напоминания всем пользователям у которых сейчас время напоминания."""
    now_utc = datetime.now(pytz.utc)

    async with AsyncSessionLocal() as db:
        users = await queries.get_all_groups_with_reminders(db)

    for user_row in users:
        try:
            tz_name = user_row.get("timezone") or "Europe/Moscow"
            reminder_time = user_row.get("reminder_time") or "22:00"

            tz = pytz.timezone(tz_name)
            now_local = now_utc.astimezone(tz)
            current_time = now_local.strftime("%H:%M")

            if current_time != reminder_time:
                continue

            telegram_id = user_row.get("telegram_id")
            if not telegram_id:
                continue

            group_id = user_row.get("group_id")
            month = now_local.strftime("%Y-%m")

            async with AsyncSessionLocal() as db:
                total_spent = await queries.get_total_spent_for_month(
                    db, group_id, month, exclude_budget_excluded=True
                )
                total_budget = await queries.get_budget(db, group_id, month)

            if total_budget:
                remaining = total_budget - total_spent
                pct = (total_spent / total_budget * 100) if total_budget > 0 else 0
                text = (
                    f"🔔 Напоминание об учёте расходов!\n\n"
                    f"💸 Потрачено за месяц: {total_spent:,.0f} ₽ ({pct:.0f}%)\n"
                    f"✅ Остаток бюджета: {remaining:,.0f} ₽\n\n"
                    "Не забудьте записать сегодняшние траты!"
                )
            else:
                text = (
                    f"🔔 Напоминание об учёте расходов!\n\n"
                    f"💸 Потрачено за месяц: {total_spent:,.0f} ₽\n\n"
                    "Не забудьте записать сегодняшние траты!"
                )

            await bot.send_message(chat_id=telegram_id, text=text)
            logger.info(f"Напоминание отправлено пользователю {telegram_id}")

        except Exception as e:
            logger.warning(f"Ошибка отправки напоминания: {e}")


def setup_scheduler(application: Application) -> None:
    """Настроить планировщик напоминаний."""
    from telegram.ext import JobQueue

    job_queue = application.job_queue
    if job_queue is None:
        logger.warning("JobQueue недоступен — напоминания не будут работать")
        return

    # Проверяем каждую минуту
    job_queue.run_repeating(
        callback=lambda ctx: send_reminders(ctx.bot),
        interval=60,
        first=10,
        name="reminders",
    )
    logger.info("Планировщик напоминаний настроен")
