from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    Integer, String, Text, Boolean, Numeric, BigInteger,
    DateTime, ForeignKey, UniqueConstraint, CheckConstraint,
    JSON, func
)
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Group(Base):
    """Группа пользователей (тенант)."""
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    invite_code: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True)
    max_members: Mapped[int] = mapped_column(Integer, default=5)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="group", cascade="all, delete-orphan")
    categories: Mapped[List["Category"]] = relationship("Category", back_populates="group", cascade="all, delete-orphan")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="group", cascade="all, delete-orphan")
    budget: Mapped[List["Budget"]] = relationship("Budget", back_populates="group", cascade="all, delete-orphan")
    budget_by_category: Mapped[List["BudgetByCategory"]] = relationship("BudgetByCategory", back_populates="group", cascade="all, delete-orphan")
    settings: Mapped[Optional["GroupSettings"]] = relationship("GroupSettings", back_populates="group", uselist=False, cascade="all, delete-orphan")
    invite_codes: Mapped[List["InviteCode"]] = relationship("InviteCode", back_populates="group", cascade="all, delete-orphan")
    activity_logs: Mapped[List["ActivityLog"]] = relationship("ActivityLog", back_populates="group")


class User(Base):
    """Пользователь (веб + Telegram)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Веб-авторизация
    web_login: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    web_password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Telegram
    telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, unique=True, nullable=True)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Роль в группе
    role: Mapped[str] = mapped_column(String(20), default="member")

    # Привязка Telegram
    link_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    link_code_expires: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Настройки
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Метаданные
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'member')", name="check_role"),
    )

    # Relationships
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="users")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="user")
    activity_logs: Mapped[List["ActivityLog"]] = relationship("ActivityLog", back_populates="user")


class Category(Base):
    """Категория трат (у каждой группы свои)."""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    emoji: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    exclude_from_budget: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("group_id", "name", name="uq_category_group_name"),
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="categories")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="category")
    budget_by_category: Mapped[List["BudgetByCategory"]] = relationship("BudgetByCategory", back_populates="category", cascade="all, delete-orphan")


class Expense(Base):
    """Трата."""
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="expenses")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="expenses")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="expenses")


class Budget(Base):
    """Бюджет на месяц."""
    __tablename__ = "budget"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2024-11"
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "month", name="uq_budget_group_month"),
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="budget")


class BudgetByCategory(Base):
    """Лимит бюджета по категории."""
    __tablename__ = "budget_by_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    month: Mapped[str] = mapped_column(String(7), nullable=False)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    __table_args__ = (
        UniqueConstraint("group_id", "month", "category_id", name="uq_budget_cat_group_month_cat"),
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="budget_by_category")
    category: Mapped["Category"] = relationship("Category", back_populates="budget_by_category")


class GroupSettings(Base):
    """Настройки группы."""
    __tablename__ = "group_settings"

    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    reminder_time: Mapped[str] = mapped_column(String(5), default="22:00")
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    currency: Mapped[str] = mapped_column(String(10), default="₽")

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="settings")


class Admin(Base):
    """Администратор сервиса (не путать с admin группы)."""
    __tablename__ = "admins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    totp_secret: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ActivityLog(Base):
    """Лог действий для аудита."""
    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)  # IPv4/IPv6
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    group: Mapped[Optional["Group"]] = relationship("Group", back_populates="activity_logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="activity_logs")


class InviteCode(Base):
    """История инвайт-кодов."""
    __tablename__ = "invite_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    used_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    group: Mapped["Group"] = relationship("Group", back_populates="invite_codes")
