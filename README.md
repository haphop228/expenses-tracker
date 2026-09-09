# 💰 Expenses Tracker — Мультитенантный сервис учёта расходов

Мультитенантный сервис учёта расходов с Telegram-ботом, веб-интерфейсом и админ-панелью.

## 🏗️ Архитектура

```
Nginx (80/443)
├── /api/*      → FastAPI (Python)
└── /*          → React (Frontend)

FastAPI ←→ PostgreSQL 16
FastAPI ←→ Redis 7
Bot     ←→ PostgreSQL 16
Bot     ←→ Redis 7
```

## 🛠️ Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Backend API | FastAPI + SQLAlchemy (async) |
| Bot | python-telegram-bot 22.7 |
| Frontend | React + Vite + TailwindCSS |
| База данных | PostgreSQL 16 |
| Кэш/Сессии | Redis 7 |
| Reverse Proxy | Nginx |
| Контейнеры | Docker Compose |

## 📁 Структура проекта

```
expenses-tracker/
├── docker-compose.yml          # Продакшен
├── docker-compose.dev.yml      # Разработка
├── .env.example                # Пример переменных
├── .gitignore
│
├── api/                        # FastAPI бэкенд
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── requirements.txt
│   └── main.py
│
├── bot/                        # Telegram бот
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── requirements.txt
│   └── main.py
│
├── frontend/                   # React приложение
│   ├── Dockerfile
│   ├── nginx.conf
│   └── src/
│
├── nginx/
│   └── nginx.conf              # Reverse proxy конфиг
│
├── scripts/
│   ├── init_db.sql             # Схема БД
│   ├── migrate_sqlite_to_postgres.py
│   ├── backup.sh
│   └── restore.sh
│
└── backups/                    # Локальные бэкапы
    ├── daily/
    ├── weekly/
    └── monthly/
```

## 🚀 Быстрый старт

### Разработка

```bash
# 1. Клонировать репозиторий
git clone <repo-url>
cd expenses-tracker

# 2. Создать .env файл
cp .env.example .env
# Заполнить BOT_TOKEN и другие переменные

# 3. Запустить в режиме разработки
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# API доступен на: http://localhost:8000
# Swagger UI:      http://localhost:8000/docs
# Frontend:        http://localhost:5173
# Adminer (БД):    http://localhost:8080
```

### Продакшен

Подробная и актуальная процедура обновления production и настройки TLS описана
в [DEPLOYMENT.md](DEPLOYMENT.md).

```bash
# 1. Подготовить сервер (Ubuntu 20.04+)
# 2. Установить Docker и Docker Compose
# 3. Настроить домен и DNS

# 4. Клонировать репозиторий
git clone <repo-url>
cd expenses-tracker

# 5. Создать .env файл
cp .env.example .env
nano .env  # Заполнить все переменные

# 6. До первого запуска получить начальный SSL-сертификат,
#    пока порт 80 ещё свободен
sudo certbot certonly --standalone -d yourdomain.com

# 7. Запустить сервисы
docker-compose up -d

# 8. Перевести последующие продления на webroot без остановки Nginx
sudo ./scripts/configure_certbot_webroot.sh yourdomain.com

# 9. Создать первого администратора
docker-compose exec api python scripts/init_admin.py

# 10. Проверить статус
docker-compose ps
docker-compose logs -f
```

## 🔄 Миграция данных из старого бота

Если у вас есть данные в SQLite (`expenses.db`):

```bash
# Установить зависимости
pip install asyncpg

# Запустить миграцию
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path /path/to/expenses.db \
    --group-name "Название группы" \
    --postgres-url "postgresql://expenses_user:password@localhost:5432/expenses" \
    --admin-telegram-ids 123456789

# Dry run (только показать что будет перенесено)
python scripts/migrate_sqlite_to_postgres.py \
    --sqlite-path /path/to/expenses.db \
    --group-name "Название группы" \
    --postgres-url "postgresql://expenses_user:password@localhost:5432/expenses" \
    --dry-run
```

## 💾 Бэкапы

```bash
# Создать бэкап вручную
./scripts/backup.sh daily

# Восстановить из бэкапа
./scripts/restore.sh backups/daily/backup_2024-11-14_03-00.sql.gz

# Настроить автоматические бэкапы (cron)
# 0 3 * * * cd /path/to/expenses-tracker && ./scripts/backup.sh daily
# 0 3 * * 0 cd /path/to/expenses-tracker && ./scripts/backup.sh weekly
# 0 3 1 * * cd /path/to/expenses-tracker && ./scripts/backup.sh monthly
```

## 🔧 Управление

```bash
# Просмотр логов
docker-compose logs -f api
docker-compose logs -f bot

# Перезапуск сервиса
docker-compose restart api

# Остановка
docker-compose down

# Обновление (после git pull)
docker-compose build
docker-compose up -d
```

## 🔐 Переменные окружения

Смотрите [`.env.example`](.env.example) для полного списка переменных.

Обязательные:
- `POSTGRES_PASSWORD` — пароль PostgreSQL
- `REDIS_PASSWORD` — пароль Redis
- `JWT_SECRET` — секрет для JWT токенов (генерация: `openssl rand -hex 32`)
- `BOT_TOKEN` — токен Telegram бота
- `ADMIN_TELEGRAM_ID` — Telegram ID для уведомлений

## 📚 Документация

- [Архитектурный план](../bot_expences/plans/multitenancy-architecture.md)
- [API спецификация](../bot_expences/plans/api-endpoints.md)
- [Docker инфраструктура](../bot_expences/plans/docker-infrastructure.md)

## 🌐 API

После запуска Swagger UI доступен по адресу:
- Разработка: http://localhost:8000/docs
- Продакшен: https://yourdomain.com/api/docs
