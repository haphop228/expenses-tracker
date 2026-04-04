-- ============================================================
-- Инициализация схемы базы данных
-- Мультитенантный сервис учёта расходов
-- ============================================================

-- ==================== МУЛЬТИТЕНАНТНОСТЬ ====================

-- Группы (тенанты)
CREATE TABLE IF NOT EXISTS groups (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    invite_code VARCHAR(64) UNIQUE,
    max_members INTEGER DEFAULT 5,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Пользователи (веб + Telegram)
CREATE TABLE IF NOT EXISTS users (
    id                SERIAL PRIMARY KEY,
    group_id          INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    name              VARCHAR(255) NOT NULL,

    -- Веб-авторизация
    web_login         VARCHAR(100) UNIQUE,
    web_password_hash VARCHAR(255),

    -- Telegram-авторизация
    telegram_id       BIGINT UNIQUE,
    telegram_username VARCHAR(100),

    -- Роль в группе
    role              VARCHAR(20) DEFAULT 'member',

    -- Привязка Telegram (временный код)
    link_code         VARCHAR(32),
    link_code_expires TIMESTAMP WITH TIME ZONE,

    -- Настройки
    reminder_enabled  BOOLEAN DEFAULT TRUE,

    -- Метаданные
    created_at        TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen         TIMESTAMP WITH TIME ZONE,

    CONSTRAINT check_role CHECK (role IN ('admin', 'member'))
);

-- Индексы для пользователей
CREATE INDEX IF NOT EXISTS idx_users_group_id ON users(group_id);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_web_login ON users(web_login);
CREATE INDEX IF NOT EXISTS idx_users_link_code ON users(link_code) WHERE link_code IS NOT NULL;

-- ==================== ОСНОВНЫЕ ДАННЫЕ ====================

-- Категории (у каждой группы свои)
CREATE TABLE IF NOT EXISTS categories (
    id                  SERIAL PRIMARY KEY,
    group_id            INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    name                VARCHAR(100) NOT NULL,
    emoji               VARCHAR(10),
    exclude_from_budget BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(group_id, name)
);

CREATE INDEX IF NOT EXISTS idx_categories_group_id ON categories(group_id);

-- Траты
CREATE TABLE IF NOT EXISTS expenses (
    id          SERIAL PRIMARY KEY,
    group_id    INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    amount      NUMERIC(12, 2) NOT NULL,
    comment     TEXT,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_expenses_group_id ON expenses(group_id);
CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id);
CREATE INDEX IF NOT EXISTS idx_expenses_category_id ON expenses(category_id);
CREATE INDEX IF NOT EXISTS idx_expenses_created_at ON expenses(created_at);
-- Составной индекс для частых запросов (группа + дата)
CREATE INDEX IF NOT EXISTS idx_expenses_group_created ON expenses(group_id, created_at);

-- Бюджет на месяц
CREATE TABLE IF NOT EXISTS budget (
    id       SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    month    VARCHAR(7) NOT NULL,
    amount   NUMERIC(12, 2) NOT NULL,

    UNIQUE(group_id, month)
);

CREATE INDEX IF NOT EXISTS idx_budget_group_id ON budget(group_id);

-- Лимиты по категориям
CREATE TABLE IF NOT EXISTS budget_by_category (
    id          SERIAL PRIMARY KEY,
    group_id    INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    month       VARCHAR(7) NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
    amount      NUMERIC(12, 2) NOT NULL,

    UNIQUE(group_id, month, category_id)
);

CREATE INDEX IF NOT EXISTS idx_budget_by_category_group_id ON budget_by_category(group_id);

-- Настройки группы
CREATE TABLE IF NOT EXISTS group_settings (
    group_id      INTEGER PRIMARY KEY REFERENCES groups(id) ON DELETE CASCADE,
    reminder_time VARCHAR(5) DEFAULT '22:00',
    timezone      VARCHAR(50) DEFAULT 'Europe/Moscow',
    currency      VARCHAR(10) DEFAULT '₽'
);

-- ==================== АДМИНИСТРИРОВАНИЕ ====================

-- Администраторы сервиса (не путать с admin группы)
CREATE TABLE IF NOT EXISTS admins (
    id            SERIAL PRIMARY KEY,
    login         VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    totp_secret   VARCHAR(64) NOT NULL,
    created_at    TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Лог действий (для аудита и админки)
CREATE TABLE IF NOT EXISTS activity_log (
    id         SERIAL PRIMARY KEY,
    group_id   INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    action     VARCHAR(100) NOT NULL,
    details    JSONB,
    ip_address INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_activity_log_group_id ON activity_log(group_id);
CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at);

-- Инвайт-коды (история)
CREATE TABLE IF NOT EXISTS invite_codes (
    id         SERIAL PRIMARY KEY,
    group_id   INTEGER REFERENCES groups(id) ON DELETE CASCADE,
    code       VARCHAR(64) UNIQUE NOT NULL,
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    used_by    INTEGER REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at    TIMESTAMP WITH TIME ZONE,
    is_active  BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invite_codes_code ON invite_codes(code);
CREATE INDEX IF NOT EXISTS idx_invite_codes_group_id ON invite_codes(group_id);
CREATE INDEX IF NOT EXISTS idx_invite_codes_active ON invite_codes(is_active) WHERE is_active = TRUE;
