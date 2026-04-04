import calendar
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from database import get_db
from models.models import Budget, BudgetByCategory, Expense, Category, User
from schemas.schemas import (
    BudgetResponse, BudgetSet, BudgetCategorySet,
    BudgetCategoryItem, MessageResponse,
)
from core.deps import get_current_active_user, require_group_admin

router = APIRouter(prefix="/budget", tags=["Budget"])


def _current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _month_bounds(month: str):
    """Вернуть (dt_from, dt_to, days_in_month) для месяца YYYY-MM."""
    try:
        year, mon = map(int, month.split("-"))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Неверный формат месяца (ожидается YYYY-MM)")
    last_day = calendar.monthrange(year, mon)[1]
    dt_from = datetime(year, mon, 1, 0, 0, 0, tzinfo=timezone.utc)
    dt_to = datetime(year, mon, last_day, 23, 59, 59, tzinfo=timezone.utc)
    return dt_from, dt_to, last_day


@router.get("", response_model=BudgetResponse)
async def get_budget(
    month: Optional[str] = Query(None, description="Месяц YYYY-MM (по умолчанию текущий)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить бюджет и статистику трат за месяц."""
    if not month:
        month = _current_month()

    dt_from, dt_to, days_in_month = _month_bounds(month)

    # Общий бюджет на месяц
    budget_result = await db.execute(
        select(Budget).where(
            Budget.group_id == current_user.group_id,
            Budget.month == month,
        )
    )
    budget_obj = budget_result.scalar_one_or_none()
    total_budget = budget_obj.amount if budget_obj else None

    # Общие траты за месяц (без исключённых категорий)
    excl_result = await db.execute(
        select(Category.id).where(
            Category.group_id == current_user.group_id,
            Category.exclude_from_budget == True,
        )
    )
    excluded_ids = [row[0] for row in excl_result.all()]

    spent_filters = [
        Expense.group_id == current_user.group_id,
        Expense.created_at >= dt_from,
        Expense.created_at <= dt_to,
    ]
    if excluded_ids:
        spent_filters.append(Expense.category_id.notin_(excluded_ids))

    spent_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), Decimal("0"))).where(and_(*spent_filters))
    )
    total_spent = spent_result.scalar_one() or Decimal("0")

    # Вычисляем оставшиеся дни
    today = date.today()
    year, mon = map(int, month.split("-"))
    if today.year == year and today.month == mon:
        days_remaining = days_in_month - today.day
        days_passed = today.day
    elif date(year, mon, 1) > today:
        days_remaining = days_in_month
        days_passed = 0
    else:
        days_remaining = 0
        days_passed = days_in_month

    # Прогноз
    remaining = None
    percentage_used = None
    daily_budget_remaining = None
    forecast = None
    forecast_over_budget = None

    if total_budget is not None:
        remaining = total_budget - total_spent
        percentage_used = float(total_spent) / float(total_budget) * 100 if total_budget > 0 else 0.0

        if days_remaining > 0 and remaining > 0:
            daily_budget_remaining = remaining / Decimal(str(days_remaining))
        elif days_remaining > 0:
            daily_budget_remaining = Decimal("0")

        if days_passed > 0:
            daily_avg = total_spent / Decimal(str(days_passed))
            forecast = daily_avg * Decimal(str(days_in_month))
            if forecast > total_budget:
                forecast_over_budget = forecast - total_budget

    # Статистика по категориям с лимитами
    cats_result = await db.execute(
        select(Category).where(
            Category.group_id == current_user.group_id,
            Category.exclude_from_budget == False,
        ).order_by(Category.name)
    )
    categories = cats_result.scalars().all()

    by_category = []
    for cat in categories:
        # Лимит по категории
        cat_budget_result = await db.execute(
            select(BudgetByCategory).where(
                BudgetByCategory.group_id == current_user.group_id,
                BudgetByCategory.month == month,
                BudgetByCategory.category_id == cat.id,
            )
        )
        cat_budget_obj = cat_budget_result.scalar_one_or_none()
        cat_budget = cat_budget_obj.amount if cat_budget_obj else None

        # Траты по категории
        cat_spent_result = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), Decimal("0"))).where(
                Expense.group_id == current_user.group_id,
                Expense.category_id == cat.id,
                Expense.created_at >= dt_from,
                Expense.created_at <= dt_to,
            )
        )
        cat_spent = cat_spent_result.scalar_one() or Decimal("0")

        cat_remaining = None
        cat_percentage = None
        if cat_budget is not None:
            cat_remaining = cat_budget - cat_spent
            cat_percentage = float(cat_spent) / float(cat_budget) * 100 if cat_budget > 0 else 0.0

        by_category.append(BudgetCategoryItem(
            category_id=cat.id,
            category_name=cat.name,
            category_emoji=cat.emoji,
            budget=cat_budget,
            spent=cat_spent,
            remaining=cat_remaining,
            percentage_used=round(cat_percentage, 2) if cat_percentage is not None else None,
        ))

    return BudgetResponse(
        month=month,
        total_budget=total_budget,
        total_spent=total_spent,
        remaining=remaining,
        percentage_used=round(percentage_used, 2) if percentage_used is not None else None,
        days_remaining=days_remaining,
        daily_budget_remaining=daily_budget_remaining,
        forecast=forecast,
        forecast_over_budget=forecast_over_budget,
        by_category=by_category,
    )


@router.post("/set", response_model=MessageResponse)
async def set_budget(
    data: BudgetSet,
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Установить общий бюджет на месяц (только admin группы)."""
    result = await db.execute(
        select(Budget).where(
            Budget.group_id == current_user.group_id,
            Budget.month == data.month,
        )
    )
    budget_obj = result.scalar_one_or_none()

    if budget_obj:
        budget_obj.amount = data.amount
    else:
        budget_obj = Budget(
            group_id=current_user.group_id,
            month=data.month,
            amount=data.amount,
        )
        db.add(budget_obj)

    await db.commit()
    return MessageResponse(message=f"Бюджет на {data.month} установлен: {data.amount}")


@router.post("/set-category", response_model=MessageResponse)
async def set_budget_for_category(
    data: BudgetCategorySet,
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Установить лимит бюджета для категории (только admin группы)."""
    # Проверяем что категория принадлежит группе
    cat_result = await db.execute(
        select(Category).where(
            Category.id == data.category_id,
            Category.group_id == current_user.group_id,
        )
    )
    if not cat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Категория не найдена")

    result = await db.execute(
        select(BudgetByCategory).where(
            BudgetByCategory.group_id == current_user.group_id,
            BudgetByCategory.month == data.month,
            BudgetByCategory.category_id == data.category_id,
        )
    )
    bbc = result.scalar_one_or_none()

    if bbc:
        bbc.amount = data.amount
    else:
        bbc = BudgetByCategory(
            group_id=current_user.group_id,
            month=data.month,
            category_id=data.category_id,
            amount=data.amount,
        )
        db.add(bbc)

    await db.commit()
    return MessageResponse(message=f"Лимит для категории {data.category_id} на {data.month} установлен: {data.amount}")
