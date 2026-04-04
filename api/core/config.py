from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List


class Settings(BaseSettings):
    # ==================== База данных ====================
    DATABASE_URL: str

    # ==================== Redis ====================
    REDIS_URL: str

    # ==================== JWT ====================
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==================== Telegram ====================
    BOT_TOKEN: str
    ADMIN_TELEGRAM_ID: Optional[int] = None

    # ==================== Настройки ====================
    TIMEZONE: str = "Europe/Moscow"
    DOMAIN: str = "localhost"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # ==================== Frontend ====================
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL должен начинаться с postgresql")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
