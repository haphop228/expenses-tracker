from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.models import Category, Expense
from schemas.schemas import CategoryResponse, CategoryCreate, CategoryUpdate, MessageResponse
from core.deps import get_current_active_user, require_group_admin
from models.models import User

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=List[CategoryResponse])
async def list_categories(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список категорий группы."""
    result = await db.execute(
        select(Category)
        .where(Category.group_id == current_user.group_id)
        .order_by(Category.name)
    )
    categories = result.scalars().all()
    return categories


@router.post("", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новую категорию (только admin группы)."""
    # Проверяем уникальность имени в группе
    result = await db.execute(
        select(Category).where(
            Category.group_id == current_user.group_id,
            Category.name == data.name,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Категория с таким именем уже существует",
        )

    category = Category(
        group_id=current_user.group_id,
        name=data.name,
        emoji=data.emoji,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить категорию (только admin группы)."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.group_id == current_user.group_id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )

    # Проверяем уникальность нового имени
    if data.name and data.name != category.name:
        result = await db.execute(
            select(Category).where(
                Category.group_id == current_user.group_id,
                Category.name == data.name,
                Category.id != category_id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Категория с таким именем уже существует",
            )
        category.name = data.name

    if data.emoji is not None:
        category.emoji = data.emoji

    if data.exclude_from_budget is not None:
        category.exclude_from_budget = data.exclude_from_budget

    await db.commit()
    await db.refresh(category)
    return category


@router.delete("/{category_id}", response_model=MessageResponse)
async def delete_category(
    category_id: int,
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить категорию (только admin группы)."""
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.group_id == current_user.group_id,
        )
    )
    category = result.scalar_one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Категория не найдена",
        )

    # Проверяем наличие трат в категории
    result = await db.execute(
        select(func.count(Expense.id)).where(Expense.category_id == category_id)
    )
    expenses_count = result.scalar_one()
    if expenses_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя удалить категорию: в ней {expenses_count} трат(ы). Сначала удалите или перенесите траты.",
        )

    await db.delete(category)
    await db.commit()
    return MessageResponse(message="Категория удалена")
