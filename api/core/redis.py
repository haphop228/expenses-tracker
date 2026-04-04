from typing import Optional
import redis.asyncio as aioredis

from core.config import settings

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Получить клиент Redis (singleton)."""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


async def close_redis():
    """Закрыть соединение с Redis."""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ==================== Вспомогательные функции ====================

async def set_with_ttl(key: str, value: str, ttl_seconds: int) -> None:
    """Сохранить значение с TTL."""
    r = await get_redis()
    await r.setex(key, ttl_seconds, value)


async def get_value(key: str) -> Optional[str]:
    """Получить значение по ключу."""
    r = await get_redis()
    return await r.get(key)


async def delete_key(key: str) -> None:
    """Удалить ключ."""
    r = await get_redis()
    await r.delete(key)


async def key_exists(key: str) -> bool:
    """Проверить существование ключа."""
    r = await get_redis()
    return bool(await r.exists(key))


# ==================== Ключи Redis ====================

def token_blacklist_key(token: str) -> str:
    """Ключ для инвалидированных токенов."""
    return f"blacklist:token:{token}"


def link_code_key(code: str) -> str:
    """Ключ для кода привязки Telegram."""
    return f"link_code:{code}"


def refresh_token_key(user_id: int, token: str) -> str:
    """Ключ для refresh токена."""
    return f"refresh:{user_id}:{token}"
