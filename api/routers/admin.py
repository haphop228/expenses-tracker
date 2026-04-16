from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.models import Admin, Group, User, Expense, GroupSettings, InviteCode
from schemas.schemas import (
    AdminLoginRequest, AdminTokenResponse,
    AdminGroupResponse, AdminGroupCreate, AdminGroupDetail,
    MemberResponse, MessageResponse, AdminResetPasswordRequest,
)
from core.security import verify_password, create_admin_token, hash_password
from core.deps import get_current_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


# ==================== Авторизация ====================

@router.post("/login", response_model=AdminTokenResponse)
async def admin_login(
    data: AdminLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Вход в панель администратора (логин + пароль + TOTP)."""
    result = await db.execute(select(Admin).where(Admin.login == data.login))
    admin = result.scalar_one_or_none()

    if not admin or not verify_password(data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    token = create_admin_token(admin.id, admin.login)
    return AdminTokenResponse(
        access_token=token,
        token_type="bearer",
        admin={"id": admin.id, "login": admin.login},
    )


# ==================== Группы ====================

@router.get("/groups", response_model=List[AdminGroupResponse])
async def list_groups(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список всех групп."""
    offset = (page - 1) * per_page
    result = await db.execute(
        select(Group).order_by(Group.created_at.desc()).offset(offset).limit(per_page)
    )
    groups = result.scalars().all()

    response = []
    now = datetime.now(timezone.utc)
    month_str = now.strftime("%Y-%m")
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    for group in groups:
        # Количество участников
        members_result = await db.execute(
            select(func.count(User.id)).where(User.group_id == group.id)
        )
        members_count = members_result.scalar_one()

        # Количество трат всего
        expenses_result = await db.execute(
            select(func.count(Expense.id)).where(Expense.group_id == group.id)
        )
        expenses_count = expenses_result.scalar_one()

        # Сумма трат за текущий месяц
        spent_result = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), Decimal("0"))).where(
                Expense.group_id == group.id,
                Expense.created_at >= month_start,
            )
        )
        total_spent_month = spent_result.scalar_one() or Decimal("0")

        # Последняя активность
        last_result = await db.execute(
            select(func.max(Expense.created_at)).where(Expense.group_id == group.id)
        )
        last_activity = last_result.scalar_one()

        response.append(AdminGroupResponse(
            id=group.id,
            name=group.name,
            members_count=members_count,
            expenses_count=expenses_count,
            total_spent_month=total_spent_month,
            last_activity=last_activity,
            created_at=group.created_at,
        ))

    return response


@router.post("/groups", response_model=AdminGroupDetail, status_code=201)
async def create_group(
    data: AdminGroupCreate,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новую группу."""
    group = Group(name=data.name, max_members=data.max_members)
    db.add(group)
    await db.flush()

    # Создаём настройки по умолчанию
    group_settings = GroupSettings(group_id=group.id)
    db.add(group_settings)

    await db.commit()
    await db.refresh(group)

    return AdminGroupDetail(
        id=group.id,
        name=group.name,
        max_members=group.max_members,
        created_at=group.created_at,
        members=[],
        statistics={},
    )


@router.get("/groups/{group_id}", response_model=AdminGroupDetail)
async def get_group_detail(
    group_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Детальная информация о группе."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    members_result = await db.execute(
        select(User).where(User.group_id == group_id).order_by(User.created_at)
    )
    members = members_result.scalars().all()

    # Статистика
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    total_expenses_result = await db.execute(
        select(func.count(Expense.id)).where(Expense.group_id == group_id)
    )
    total_expenses = total_expenses_result.scalar_one()

    month_spent_result = await db.execute(
        select(func.coalesce(func.sum(Expense.amount), Decimal("0"))).where(
            Expense.group_id == group_id,
            Expense.created_at >= month_start,
        )
    )
    month_spent = month_spent_result.scalar_one() or Decimal("0")

    return AdminGroupDetail(
        id=group.id,
        name=group.name,
        max_members=group.max_members,
        created_at=group.created_at,
        members=[MemberResponse.model_validate(m) for m in members],
        statistics={
            "total_expenses": total_expenses,
            "month_spent": float(month_spent),
            "members_count": len(members),
        },
    )


@router.delete("/groups/{group_id}", response_model=MessageResponse)
async def delete_group(
    group_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить группу со всеми данными."""
    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    await db.delete(group)
    await db.commit()
    return MessageResponse(message=f"Группа '{group.name}' удалена")


# ==================== Пользователи ====================

@router.get("/users", response_model=List[MemberResponse])
async def list_users(
    group_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список пользователей (с фильтром по группе)."""
    filters = []
    if group_id is not None:
        filters.append(User.group_id == group_id)

    offset = (page - 1) * per_page
    query = select(User).order_by(User.created_at.desc()).offset(offset).limit(per_page)
    if filters:
        from sqlalchemy import and_
        query = query.where(and_(*filters))

    result = await db.execute(query)
    users = result.scalars().all()
    return [MemberResponse.model_validate(u) for u in users]


@router.post("/users/{user_id}/reset-password", response_model=MessageResponse)
async def reset_user_password(
    user_id: int,
    data: AdminResetPasswordRequest,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Сбросить пароль пользователя (от имени администратора)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    user.web_password_hash = hash_password(data.new_password)
    await db.commit()
    return MessageResponse(message=f"Пароль пользователя '{user.name}' сброшен")


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить пользователя."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    await db.delete(user)
    await db.commit()
    return MessageResponse(message=f"Пользователь '{user.name}' удалён")


# ==================== Инвайты ====================

@router.post("/groups/{group_id}/invite", response_model=dict)
async def admin_create_invite(
    group_id: int,
    admin: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать инвайт-код для группы (от имени администратора сервиса)."""
    from datetime import timedelta
    from core.security import generate_invite_code

    result = await db.execute(select(Group).where(Group.id == group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    code = generate_invite_code()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

    invite = InviteCode(
        group_id=group_id,
        code=code,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()

    return {
        "code": code,
        "group_id": group_id,
        "expires_at": expires_at.isoformat(),
    }
