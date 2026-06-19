import math
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from database import get_db
from models.models import Expense, Category, User
from schemas.schemas import (
    ExpenseResponse, ExpenseCreate, ExpenseUpdate,
    PaginatedExpenses, MessageResponse,
)
from core.deps import get_current_active_user

router = APIRouter(prefix="/expenses", tags=["Expenses"])


def _build_expense_response(expense: Expense) -> ExpenseResponse:
    """Собрать ExpenseResponse из ORM-объекта с joined данными."""
    return ExpenseResponse(
        id=expense.id,
        user_id=expense.user_id,
        user_name=expense.user.name if expense.user else None,
        category_id=expense.category_id,
        category_name=expense.category.name if expense.category else None,
        category_emoji=expense.category.emoji if expense.category else None,
        amount=expense.amount,
        comment=expense.comment,
        created_at=expense.created_at,
    )


@router.get("", response_model=PaginatedExpenses)
async def list_expenses(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    date_from: Optional[str] = Query(None, description="Дата от (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Дата до (YYYY-MM-DD)"),
    category_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список трат группы с пагинацией и фильтрами."""
    filters = [Expense.group_id == current_user.group_id]

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            filters.append(Expense.created_at >= dt_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат date_from (ожидается YYYY-MM-DD)")

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            filters.append(Expense.created_at <= dt_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат date_to (ожидается YYYY-MM-DD)")

    if category_id is not None:
        filters.append(Expense.category_id == category_id)

    if user_id is not None:
        filters.append(Expense.user_id == user_id)

    # Считаем общее количество
    count_result = await db.execute(
        select(func.count(Expense.id)).where(and_(*filters))
    )
    total = count_result.scalar_one()

    # Получаем страницу с joined данными
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Expense)
        .where(and_(*filters))
        .order_by(Expense.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    expenses = result.scalars().all()

    # Загружаем связанные данные
    items = []
    for expense in expenses:
        # Загружаем user
        if expense.user_id:
            user_result = await db.execute(select(User).where(User.id == expense.user_id))
            expense.user = user_result.scalar_one_or_none()
        else:
            expense.user = None

        # Загружаем category
        if expense.category_id:
            cat_result = await db.execute(select(Category).where(Category.id == expense.category_id))
            expense.category = cat_result.scalar_one_or_none()
        else:
            expense.category = None

        items.append(_build_expense_response(expense))

    pages = math.ceil(total / per_page) if total > 0 else 1

    return PaginatedExpenses(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.post("", response_model=ExpenseResponse, status_code=201)
async def create_expense(
    data: ExpenseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Добавить трату."""
    # Проверяем что категория принадлежит группе
    result = await db.execute(
        select(Category).where(
            Category.id == data.category_id,
            Category.group_id == current_user.group_id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )

    created_at = data.created_at or datetime.now(timezone.utc)

    expense = Expense(
        group_id=current_user.group_id,
        user_id=current_user.id,
        category_id=data.category_id,
        amount=data.amount,
        comment=data.comment,
        created_at=created_at,
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)

    return ExpenseResponse(
        id=expense.id,
        user_id=expense.user_id,
        user_name=current_user.name,
        category_id=expense.category_id,
        category_name=category.name,
        category_emoji=category.emoji,
        amount=expense.amount,
        comment=expense.comment,
        created_at=expense.created_at,
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить трату по ID."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.group_id == current_user.group_id,
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Трата не найдена",
        )

    # Загружаем связанные данные
    user_obj = None
    if expense.user_id:
        user_result = await db.execute(select(User).where(User.id == expense.user_id))
        user_obj = user_result.scalar_one_or_none()

    category_obj = None
    if expense.category_id:
        cat_result = await db.execute(select(Category).where(Category.id == expense.category_id))
        category_obj = cat_result.scalar_one_or_none()

    return ExpenseResponse(
        id=expense.id,
        user_id=expense.user_id,
        user_name=user_obj.name if user_obj else None,
        category_id=expense.category_id,
        category_name=category_obj.name if category_obj else None,
        category_emoji=category_obj.emoji if category_obj else None,
        amount=expense.amount,
        comment=expense.comment,
        created_at=expense.created_at,
    )


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    data: ExpenseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить трату (только свою, или admin группы может любую)."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.group_id == current_user.group_id,
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Трата не найдена",
        )

    # Проверяем права: только своя трата или admin
    if expense.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для редактирования этой траты",
        )

    if data.category_id is not None:
        # Проверяем что новая категория принадлежит группе
        cat_result = await db.execute(
            select(Category).where(
                Category.id == data.category_id,
                Category.group_id == current_user.group_id,
            )
        )
        if not cat_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Категория не найдена",
            )
        expense.category_id = data.category_id

    if data.amount is not None:
        expense.amount = data.amount

    if data.comment is not None:
        expense.comment = data.comment

    if data.created_at is not None:
        expense.created_at = data.created_at

    await db.commit()
    await db.refresh(expense)

    # Загружаем связанные данные для ответа
    user_obj = None
    if expense.user_id:
        user_result = await db.execute(select(User).where(User.id == expense.user_id))
        user_obj = user_result.scalar_one_or_none()

    category_obj = None
    if expense.category_id:
        cat_result = await db.execute(select(Category).where(Category.id == expense.category_id))
        category_obj = cat_result.scalar_one_or_none()

    return ExpenseResponse(
        id=expense.id,
        user_id=expense.user_id,
        user_name=user_obj.name if user_obj else None,
        category_id=expense.category_id,
        category_name=category_obj.name if category_obj else None,
        category_emoji=category_obj.emoji if category_obj else None,
        amount=expense.amount,
        comment=expense.comment,
        created_at=expense.created_at,
    )


@router.delete("/{expense_id}", response_model=MessageResponse)
async def delete_expense(
    expense_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить трату (только свою, или admin группы может любую)."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.group_id == current_user.group_id,
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Трата не найдена",
        )

    # Проверяем права: только своя трата или admin
    if expense.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет прав для удаления этой траты",
        )

    await db.delete(expense)
    await db.commit()
    return MessageResponse(message="Трата удалена")
