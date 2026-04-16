from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


# ==================== ГРУППЫ ====================

class GroupSettingsSchema(BaseModel):
    reminder_time: str = "22:00"
    timezone: str = "Europe/Moscow"
    currency: str = "₽"

    model_config = {"from_attributes": True}


class GroupSettingsUpdate(BaseModel):
    reminder_time: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None

    @field_validator("reminder_time")
    @classmethod
    def validate_time(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        parts = v.split(":")
        if len(parts) != 2:
            raise ValueError("Формат времени: HH:MM")
        h, m = parts
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            raise ValueError("Некорректное время")
        return v


class GroupResponse(BaseModel):
    id: int
    name: str
    max_members: int
    created_at: datetime
    settings: Optional[GroupSettingsSchema] = None

    model_config = {"from_attributes": True}


class GroupDetailResponse(GroupResponse):
    current_members: int = 0


# ==================== ПОЛЬЗОВАТЕЛИ ====================

class UserResponse(BaseModel):
    id: int
    group_id: Optional[int]
    name: str
    web_login: Optional[str]
    telegram_id: Optional[int]
    telegram_username: Optional[str]
    role: str
    reminder_enabled: bool
    created_at: datetime
    last_seen: Optional[datetime]

    model_config = {"from_attributes": True}


class UserMeResponse(UserResponse):
    group_name: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    reminder_enabled: Optional[bool] = None


# ==================== АВТОРИЗАЦИЯ ====================

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=100)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    web_login: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_]+$")
    web_password: str = Field(..., min_length=8, max_length=100)


class LoginRequest(BaseModel):
    web_login: str
    web_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LinkCodeResponse(BaseModel):
    link_code: str
    expires_at: datetime
    command: str


class BotLinkRequest(BaseModel):
    link_code: str
    telegram_id: int
    telegram_username: Optional[str] = None


# ==================== КАТЕГОРИИ ====================

class CategoryResponse(BaseModel):
    id: int
    name: str
    emoji: Optional[str]
    exclude_from_budget: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    emoji: Optional[str] = Field(None, max_length=10)


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    emoji: Optional[str] = Field(None, max_length=10)
    exclude_from_budget: Optional[bool] = None


# ==================== ТРАТЫ ====================

class ExpenseUserInfo(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class ExpenseCategoryInfo(BaseModel):
    id: int
    name: str
    emoji: Optional[str]

    model_config = {"from_attributes": True}


class ExpenseResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_name: Optional[str] = None
    category_id: Optional[int]
    category_name: Optional[str] = None
    category_emoji: Optional[str] = None
    amount: Decimal
    comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ExpenseCreate(BaseModel):
    category_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    comment: Optional[str] = Field(None, max_length=500)
    created_at: Optional[datetime] = None  # Для указания даты вручную


class ExpenseUpdate(BaseModel):
    category_id: Optional[int] = None
    amount: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    comment: Optional[str] = Field(None, max_length=500)


class PaginatedExpenses(BaseModel):
    items: List[ExpenseResponse]
    total: int
    page: int
    per_page: int
    pages: int


# ==================== СТАТИСТИКА ====================

class CategoryStats(BaseModel):
    category_id: Optional[int]
    category_name: Optional[str]
    category_emoji: Optional[str]
    total: Decimal
    count: int
    percentage: float


class UserStats(BaseModel):
    user_id: int
    user_name: str
    total: Decimal
    count: int
    percentage: float


class StatsSummaryResponse(BaseModel):
    total_amount: Decimal
    total_count: int
    average_per_day: Decimal
    by_category: List[CategoryStats]
    by_user: List[UserStats]


# ==================== БЮДЖЕТ ====================

class BudgetCategoryItem(BaseModel):
    category_id: int
    category_name: str
    category_emoji: Optional[str]
    budget: Optional[Decimal]
    spent: Decimal
    remaining: Optional[Decimal]
    percentage_used: Optional[float]


class BudgetResponse(BaseModel):
    month: str
    total_budget: Optional[Decimal]
    total_spent: Decimal
    remaining: Optional[Decimal]
    percentage_used: Optional[float]
    days_remaining: int
    daily_budget_remaining: Optional[Decimal]
    forecast: Optional[Decimal]
    forecast_over_budget: Optional[Decimal]
    by_category: List[BudgetCategoryItem]


class BudgetSet(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    amount: Decimal = Field(..., gt=0, decimal_places=2)


class BudgetCategorySet(BaseModel):
    month: str = Field(..., pattern=r"^\d{4}-\d{2}$")
    category_id: int
    amount: Decimal = Field(..., gt=0, decimal_places=2)


# ==================== ГРУППЫ (управление) ====================

class InviteResponse(BaseModel):
    code: str
    url: str
    expires_at: datetime


class MemberResponse(BaseModel):
    id: int
    name: str
    web_login: Optional[str]
    telegram_id: Optional[int]
    telegram_username: Optional[str]
    role: str
    reminder_enabled: bool
    created_at: datetime
    last_seen: Optional[datetime]

    model_config = {"from_attributes": True}


# ==================== АДМИН ====================

class AdminLoginRequest(BaseModel):
    login: str
    password: str


class AdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


class AdminGroupResponse(BaseModel):
    id: int
    name: str
    members_count: int
    expenses_count: int
    total_spent_month: Decimal
    last_activity: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    max_members: int = Field(5, ge=2, le=50)


class AdminGroupDetail(BaseModel):
    id: int
    name: str
    max_members: int
    created_at: datetime
    members: List[MemberResponse]
    statistics: dict

    model_config = {"from_attributes": True}


class BackupInfo(BaseModel):
    filename: str
    size_mb: float
    created_at: datetime
    type: str  # daily | weekly | monthly | manual


class SystemMonitor(BaseModel):
    services: dict
    system: dict


# ==================== ОБЩИЕ ====================

class HealthResponse(BaseModel):
    status: str
    database: str
    redis: str
    version: str = "1.0.0"


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None


class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
