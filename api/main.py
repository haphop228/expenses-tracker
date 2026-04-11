import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from database import engine, Base
from core.redis import get_redis

# Импорт всех моделей для создания таблиц
import models.models  # noqa: F401

# Роутеры
from routers.health import router as health_router
from routers.auth import router as auth_router
from routers.categories import router as categories_router
from routers.expenses import router as expenses_router
from routers.statistics import router as statistics_router
from routers.budget import router as budget_router
from routers.groups import router as groups_router
from routers.bot import router as bot_router
from routers.admin import router as admin_router

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения."""
    logger.info("Запуск приложения...")

    # Проверяем подключение к Redis
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis: подключение установлено")
    except Exception as e:
        logger.warning(f"Redis: не удалось подключиться — {e}")

    logger.info("Приложение запущено")
    yield

    logger.info("Завершение работы приложения...")


app = FastAPI(
    title="Expenses Tracker API",
    description="API для трекера расходов с мультитенантностью",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Подключаем роутеры
API_PREFIX = "/api/v1"

app.include_router(health_router, prefix=API_PREFIX)
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(categories_router, prefix=API_PREFIX)
app.include_router(expenses_router, prefix=API_PREFIX)
app.include_router(statistics_router, prefix=API_PREFIX)
app.include_router(budget_router, prefix=API_PREFIX)
app.include_router(groups_router, prefix=API_PREFIX)
app.include_router(bot_router, prefix=API_PREFIX)
app.include_router(admin_router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Expenses Tracker API", "docs": "/api/docs"}
