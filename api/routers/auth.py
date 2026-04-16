from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models.models import User, Group, GroupSettings, InviteCode
from schemas.schemas import (
    RegisterRequest, LoginRequest, TokenResponse, RefreshRequest,
    AccessTokenResponse, LinkCodeResponse, MessageResponse, UserMeResponse,
    ChangePasswordRequest,
)
from core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
    generate_link_code,
)
from core.redis import (
    set_with_ttl, get_value, delete_key, key_exists,
    token_blacklist_key, link_code_key, refresh_token_key,
    get_redis,
)
from core.deps import get_current_user, get_current_active_user
from core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/auth", tags=["Auth"])

# TTL для link_code: 15 минут
LINK_CODE_TTL = 15 * 60
# TTL для refresh токена в Redis
REFRESH_TOKEN_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


@router.post("/register/{invite_code}", response_model=TokenResponse, status_code=201)
async def register(
    invite_code: str,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Регистрация нового пользователя по инвайт-коду."""
    # Проверяем инвайт-код
    result = await db.execute(
        select(InviteCode).where(
            InviteCode.code == invite_code,
            InviteCode.is_active == True,
            InviteCode.expires_at > datetime.now(timezone.utc),
            InviteCode.used_by == None,
        )
    )
    invite = result.scalar_one_or_none()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Инвайт-код недействителен или истёк",
        )

    # Проверяем уникальность логина
    result = await db.execute(select(User).where(User.web_login == data.web_login))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Логин уже занят",
        )

    # Проверяем лимит участников группы
    result = await db.execute(select(Group).where(Group.id == invite.group_id))
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=400, detail="Группа не найдена")

    result = await db.execute(
        select(User).where(User.group_id == group.id)
    )
    members = result.scalars().all()
    if len(members) >= group.max_members:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Достигнут лимит участников группы",
        )

    # Определяем роль: первый участник — admin
    role = "admin" if len(members) == 0 else "member"

    # Создаём пользователя
    user = User(
        group_id=group.id,
        name=data.name,
        web_login=data.web_login,
        web_password_hash=hash_password(data.web_password),
        role=role,
    )
    db.add(user)
    await db.flush()

    # Помечаем инвайт как использованный
    invite.used_by = user.id
    invite.used_at = datetime.now(timezone.utc)
    invite.is_active = False

    await db.commit()
    await db.refresh(user)

    # Создаём токены
    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    # Сохраняем refresh токен в Redis
    await set_with_ttl(
        refresh_token_key(user.id, refresh_token),
        str(user.id),
        REFRESH_TOKEN_TTL,
    )

    from schemas.schemas import UserResponse
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Вход в систему."""
    result = await db.execute(select(User).where(User.web_login == data.web_login))
    user = result.scalar_one_or_none()

    if not user or not user.web_password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if not verify_password(data.web_password, user.web_password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    # Обновляем last_seen
    user.last_seen = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    await set_with_ttl(
        refresh_token_key(user.id, refresh_token),
        str(user.id),
        REFRESH_TOKEN_TTL,
    )

    from schemas.schemas import UserResponse
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    """Выход из системы — инвалидирует access и refresh токены."""
    if credentials:
        access_token = credentials.credentials
        payload = decode_token(access_token)
        # Добавляем access token в blacklist до истечения его TTL
        if payload:
            exp = payload.get("exp")
            now_ts = int(datetime.now(timezone.utc).timestamp())
            ttl = max(exp - now_ts, 1) if exp else settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
            await set_with_ttl(token_blacklist_key(access_token), "1", ttl)

        # Удаляем refresh токен из Redis (все сессии пользователя)
        user_id = current_user.id
        r = await get_redis()
        # Ищем все refresh-ключи этого пользователя и удаляем
        pattern = f"refresh:{user_id}:*"
        async for key in r.scan_iter(pattern):
            await r.delete(key)

    return MessageResponse(message="Выход выполнен успешно")


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Обновить access токен."""
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный refresh токен",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Недействительный токен")

    # Проверяем что refresh токен есть в Redis
    redis_key = refresh_token_key(int(user_id), data.refresh_token)
    if not await key_exists(redis_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh токен истёк или отозван",
        )

    # Проверяем пользователя
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    new_access_token = create_access_token({"sub": str(user.id)})
    return AccessTokenResponse(access_token=new_access_token)


@router.get("/me", response_model=UserMeResponse)
async def get_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить информацию о текущем пользователе."""
    group_name = None
    if current_user.group_id:
        result = await db.execute(select(Group).where(Group.id == current_user.group_id))
        group = result.scalar_one_or_none()
        group_name = group.name if group else None

    return UserMeResponse(
        **{k: v for k, v in current_user.__dict__.items() if not k.startswith("_")},
        group_name=group_name,
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Сменить пароль текущего пользователя."""
    if not current_user.web_password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя не установлен пароль",
        )
    if not verify_password(data.current_password, current_user.web_password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный текущий пароль",
        )
    current_user.web_password_hash = hash_password(data.new_password)
    await db.commit()
    return MessageResponse(message="Пароль успешно изменён")


@router.post("/generate-link-code", response_model=LinkCodeResponse)
async def generate_link_code_endpoint(
    current_user: User = Depends(get_current_active_user),
):
    """Сгенерировать код для привязки Telegram аккаунта."""
    code = generate_link_code()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=LINK_CODE_TTL)

    # Сохраняем в Redis: code -> user_id
    await set_with_ttl(
        link_code_key(code),
        str(current_user.id),
        LINK_CODE_TTL,
    )

    return LinkCodeResponse(
        link_code=code,
        expires_at=expires_at,
        command=f"/link {code}",
    )
