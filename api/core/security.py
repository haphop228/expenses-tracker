from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from jose import JWTError, jwt
import bcrypt
import pyotp

from core.config import settings


# ==================== Пароли ====================

def hash_password(password: str) -> str:
    """Хэшировать пароль."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверить пароль."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ==================== JWT токены ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создать JWT access токен."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Создать JWT refresh токен."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Декодировать JWT токен. Возвращает payload или None при ошибке."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def create_admin_token(admin_id: int, login: str) -> str:
    """Создать JWT токен для администратора сервиса."""
    data = {
        "sub": str(admin_id),
        "login": login,
        "role": "service_admin",
    }
    expire = datetime.now(timezone.utc) + timedelta(hours=8)
    data.update({"exp": expire, "type": "admin"})
    return jwt.encode(data, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ==================== TOTP (2FA) ====================

def generate_totp_secret() -> str:
    """Сгенерировать секрет для TOTP."""
    return pyotp.random_base32()


def verify_totp(secret: str, code: str) -> bool:
    """Проверить TOTP код."""
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)  # ±30 секунд


def get_totp_uri(secret: str, login: str) -> str:
    """Получить URI для QR-кода (Google Authenticator)."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=login,
        issuer_name="ExpenseTracker Admin"
    )


# ==================== Инвайт-коды ====================

import secrets
import string


def generate_invite_code(length: int = 12) -> str:
    """Сгенерировать случайный инвайт-код."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_link_code(length: int = 8) -> str:
    """Сгенерировать код для привязки Telegram (короткий, только буквы и цифры)."""
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
