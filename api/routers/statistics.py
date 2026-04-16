import calendar
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from database import get_db
from models.models import Expense, Category, User
from schemas.schemas import StatsSummaryResponse, CategoryStats, UserStats
from core.deps import get_current_active_user

router = APIRouter(prefix="/statistics", tags=["Statistics"])


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _month_bounds(month: str):
    """Вернуть (date_from, date_to) для месяца в формате YYYY-MM."""
    try:
        year, mon = map(int, month.split("-"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Неверный формат месяца (ожидается YYYY-MM)")
    last_day = calendar.monthrange(year, mon)[1]
    dt_from = datetime(year, mon, 1, 0, 0, 0, tzinfo=timezone.utc)
    dt_to = datetime(year, mon, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return dt_from, dt_to


@router.get("/summary", response_model=StatsSummaryResponse)
async def get_summary(
    month: Optional[str] = Query(None, description="Месяц YYYY-MM (по умолчанию текущий)"),
    date_from: Optional[str] = Query(None, description="Дата от YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата до YYYY-MM-DD"),
    exclude_budget_excluded: bool = Query(False, description="Исключить категории, помеченные exclude_from_budget"),
    user_id: Optional[int] = Query(None, description="Фильтр по участнику (user_id)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить сводную статистику за период (month или date_from/date_to)."""
    if date_from and date_to:
        # Режим произвольного периода
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат даты (ожидается YYYY-MM-DD)")
    else:
        if not month:
            month = _current_month()
        dt_from, dt_to = _month_bounds(month)

    # Базовые фильтры
    base_filters = [
        Expense.group_id == current_user.group_id,
        Expense.created_at >= dt_from,
        Expense.created_at <= dt_to,
    ]

    # Фильтр по участнику
    if user_id is not None:
        base_filters.append(Expense.user_id == user_id)

    # Если нужно исключить категории
    excluded_category_ids = []
    if exclude_budget_excluded:
        excl_result = await db.execute(
            select(Category.id).where(
                Category.group_id == current_user.group_id,
                Category.exclude_from_budget == True,
            )
        )
        excluded_category_ids = [row[0] for row in excl_result.all()]
        if excluded_category_ids:
            base_filters.append(Expense.category_id.notin_(excluded_category_ids))

    # Общая сумма и количество
    total_result = await db.execute(
        select(
            func.coalesce(func.sum(Expense.amount), Decimal("0")),
            func.count(Expense.id),
        ).where(and_(*base_filters))
    )
    total_amount, total_count = total_result.one()

    # Количество дней в периоде (для среднего)
    days_in_month = calendar.monthrange(dt_from.year, dt_from.month)[1]
    today = date.today()
    current_day = min(today.day, days_in_month) if (
        today.year == dt_from.year and today.month == dt_from.month
    ) else days_in_month
    average_per_day = (
        Decimal(str(total_amount)) / Decimal(str(current_day))
        if current_day > 0 and total_amount > 0
        else Decimal("0")
    )

    # Статистика по категориям
    cat_result = await db.execute(
        select(
            Expense.category_id,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        )
        .where(and_(*base_filters))
        .group_by(Expense.category_id)
        .order_by(func.sum(Expense.amount).desc())
    )
    cat_rows = cat_result.all()

    by_category = []
    for row in cat_rows:
        cat_id, cat_total, cat_count = row
        cat_name = None
        cat_emoji = None
        if cat_id:
            cat_obj_result = await db.execute(select(Category).where(Category.id == cat_id))
            cat_obj = cat_obj_result.scalar_one_or_none()
            if cat_obj:
                cat_name = cat_obj.name
                cat_emoji = cat_obj.emoji

        percentage = (
            float(cat_total) / float(total_amount) * 100
            if total_amount and total_amount > 0
            else 0.0
        )
        by_category.append(CategoryStats(
            category_id=cat_id,
            category_name=cat_name,
            category_emoji=cat_emoji,
            total=cat_total,
            count=cat_count,
            percentage=round(percentage, 2),
        ))

    # Статистика по пользователям
    user_result = await db.execute(
        select(
            Expense.user_id,
            func.sum(Expense.amount).label("total"),
            func.count(Expense.id).label("count"),
        )
        .where(and_(*base_filters), Expense.user_id.isnot(None))
        .group_by(Expense.user_id)
        .order_by(func.sum(Expense.amount).desc())
    )
    user_rows = user_result.all()

    by_user = []
    for row in user_rows:
        u_id, u_total, u_count = row
        user_obj_result = await db.execute(select(User).where(User.id == u_id))
        user_obj = user_obj_result.scalar_one_or_none()
        u_name = user_obj.name if user_obj else f"User #{u_id}"

        percentage = (
            float(u_total) / float(total_amount) * 100
            if total_amount and total_amount > 0
            else 0.0
        )
        by_user.append(UserStats(
            user_id=u_id,
            user_name=u_name,
            total=u_total,
            count=u_count,
            percentage=round(percentage, 2),
        ))

    return StatsSummaryResponse(
        total_amount=total_amount or Decimal("0"),
        total_count=total_count,
        average_per_day=average_per_day.quantize(Decimal("0.01")),
        by_category=by_category,
        by_user=by_user,
    )
