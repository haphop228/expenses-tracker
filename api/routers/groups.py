from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.models import Group, User, GroupSettings, InviteCode
from schemas.schemas import (
    GroupDetailResponse, GroupSettingsSchema, GroupSettingsUpdate,
    InviteResponse, MemberResponse, MessageResponse, UserUpdate,
)
from core.deps import get_current_active_user, require_group_admin
from core.security import generate_invite_code
from core.config import settings

router = APIRouter(prefix="/groups", tags=["Groups"])

# TTL инвайт-кода: 48 часов
INVITE_TTL_HOURS = 48


@router.get("/me", response_model=GroupDetailResponse)
async def get_my_group(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить информацию о своей группе."""
    result = await db.execute(select(Group).where(Group.id == current_user.group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    members_result = await db.execute(
        select(User).where(User.group_id == group.id)
    )
    members = members_result.scalars().all()

    settings_result = await db.execute(
        select(GroupSettings).where(GroupSettings.group_id == group.id)
    )
    group_settings = settings_result.scalar_one_or_none()

    return GroupDetailResponse(
        id=group.id,
        name=group.name,
        max_members=group.max_members,
        created_at=group.created_at,
        current_members=len(members),
        settings=GroupSettingsSchema.model_validate(group_settings) if group_settings else None,
    )


@router.get("/members", response_model=List[MemberResponse])
async def list_members(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список участников группы."""
    result = await db.execute(
        select(User)
        .where(User.group_id == current_user.group_id)
        .order_by(User.created_at)
    )
    members = result.scalars().all()
    return members


@router.post("/invite", response_model=InviteResponse)
async def create_invite(
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать инвайт-ссылку для вступления в группу (только admin)."""
    # Проверяем лимит участников
    result = await db.execute(select(Group).where(Group.id == current_user.group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")

    members_result = await db.execute(
        select(User).where(User.group_id == group.id)
    )
    members = members_result.scalars().all()
    if len(members) >= group.max_members:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Достигнут лимит участников группы",
        )

    code = generate_invite_code()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=INVITE_TTL_HOURS)

    invite = InviteCode(
        group_id=current_user.group_id,
        code=code,
        created_by=current_user.id,
        expires_at=expires_at,
    )
    db.add(invite)
    await db.commit()

    base_url = settings.FRONTEND_URL if hasattr(settings, "FRONTEND_URL") else "https://example.com"
    return InviteResponse(
        code=code,
        url=f"{base_url}/register/{code}",
        expires_at=expires_at,
    )


@router.delete("/members/{user_id}", response_model=MessageResponse)
async def remove_member(
    user_id: int,
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить участника из группы (только admin)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить самого себя",
        )

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.group_id == current_user.group_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Участник не найден")

    # Отвязываем от группы (не удаляем пользователя)
    member.group_id = None
    member.role = "member"
    await db.commit()
    return MessageResponse(message="Участник удалён из группы")


@router.put("/settings", response_model=GroupSettingsSchema)
async def update_settings(
    data: GroupSettingsUpdate,
    current_user: User = Depends(require_group_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить настройки группы (только admin)."""
    result = await db.execute(
        select(GroupSettings).where(GroupSettings.group_id == current_user.group_id)
    )
    group_settings = result.scalar_one_or_none()

    if not group_settings:
        group_settings = GroupSettings(group_id=current_user.group_id)
        db.add(group_settings)

    if data.reminder_time is not None:
        group_settings.reminder_time = data.reminder_time
    if data.timezone is not None:
        group_settings.timezone = data.timezone
    if data.currency is not None:
        group_settings.currency = data.currency

    await db.commit()
    await db.refresh(group_settings)
    return GroupSettingsSchema.model_validate(group_settings)


@router.put("/me/profile", response_model=MemberResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить свой профиль."""
    if data.name is not None:
        current_user.name = data.name
    if data.reminder_enabled is not None:
        current_user.reminder_enabled = data.reminder_enabled

    await db.commit()
    await db.refresh(current_user)
    return MemberResponse.model_validate(current_user)
