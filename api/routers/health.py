from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from database import get_db
from schemas.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    """Проверка состояния API."""
    # Проверяем БД
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Проверяем Redis
    redis_status = "connected"
    try:
        from core.redis import get_redis
        r = await get_redis()
        await r.ping()
    except Exception:
        redis_status = "error"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        redis=redis_status,
    )
