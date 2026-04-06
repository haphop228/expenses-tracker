# 🚀 QUICKSTART — Локальный запуск без DNS

Этот гайд позволяет запустить весь стек на локальной машине по адресу `http://localhost`.
Никакого домена и SSL не нужно.

## Требования

- Docker >= 24
- Docker Compose >= 2.20
- Telegram Bot Token (получить у [@BotFather](https://t.me/BotFather))

---

## Шаг 1 — Клонировать и перейти в папку

```bash
cd expenses-tracker
```

---

## Шаг 2 — Создать `.env`

```bash
cp .env.example .env
```

Открыть `.env` и заполнить обязательные поля:

```env
# База данных
POSTGRES_DB=expenses
POSTGRES_USER=expenses_user
POSTGRES_PASSWORD=mypassword123

# Redis
REDIS_PASSWORD=myredispass123

# JWT (сгенерировать: openssl rand -hex 32)
JWT_SECRET=замените_на_случайную_строку_минимум_32_символа

# Telegram
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_TELEGRAM_ID=ваш_telegram_id  # узнать у @userinfobot

# Настройки
TIMEZONE=Europe/Moscow
DOMAIN=localhost
```

---

## Шаг 3 — Запустить dev-стек

```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Первый запуск займёт 3–5 минут (скачивание образов, установка зависимостей).

Дождитесь сообщений:
```
expenses_api   | INFO:     Application startup complete.
expenses_bot   | INFO - Бот запущен
```

---

## Шаг 4 — Применить миграции БД

В **новом терминале**:

```bash
docker-compose exec api alembic upgrade head
```

---

## Шаг 5 — Создать первого администратора

```bash
docker-compose exec api python scripts/create_admin.py \
  --login admin \
  --password MyAdminPass123
```

Скрипт выведет TOTP-секрет — сохраните его и добавьте в Google Authenticator / Authy.

---

## Шаг 6 — Открыть в браузере

| Сервис | URL |
|--------|-----|
| 🌐 Веб-приложение (React) | http://localhost:5173 |
| 📖 API документация (Swagger) | http://localhost:8000/api/docs |
| 🗄️ Adminer (PostgreSQL UI) | http://localhost:8080 |

---

## Шаг 7 — Создать первую группу и пользователя

Через Swagger UI (`http://localhost:8000/api/docs`) или через API:

### 7.1 Создать группу (через admin API)

```bash
# Сначала войти как admin (получить токен)
curl -X POST http://localhost:8000/api/v1/admin/login \
  -H "Content-Type: application/json" \
  -d '{"login": "admin", "password": "MyAdminPass123", "totp_code": "123456"}'
```

> `totp_code` — текущий код из Google Authenticator

```bash
# Создать группу (подставить токен из предыдущего ответа)
curl -X POST http://localhost:8000/api/v1/admin/groups \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Моя семья", "max_members": 5}'
```

### 7.2 Создать инвайт-код

```bash
curl -X POST http://localhost:8000/api/v1/admin/groups/<GROUP_ID>/invite \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### 7.3 Зарегистрироваться по инвайт-коду

Открыть http://localhost:5173/register и ввести инвайт-код.

Или через API:
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/<INVITE_CODE> \
  -H "Content-Type: application/json" \
  -d '{"name": "Иван", "web_login": "ivan", "web_password": "password123"}'
```

### 7.4 Привязать Telegram

В личном кабинете (http://localhost:5173/settings) нажать **"Получить код привязки"**.
Скопировать команду вида `/link ABCD1234` и отправить боту в Telegram.

---

## Полезные команды

```bash
# Посмотреть логи всех сервисов
docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Логи только API
docker-compose logs -f api

# Логи только бота
docker-compose logs -f bot

# Перезапустить только API (после изменений кода)
docker-compose restart api

# Остановить всё
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down

# Остановить и удалить данные (ОСТОРОЖНО: удалит БД)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

---

## Структура портов

| Порт | Сервис | Описание |
|------|--------|----------|
| 5173 | frontend | Vite dev server (React) |
| 8000 | api | FastAPI + Swagger UI |
| 8080 | adminer | Веб-интерфейс PostgreSQL |
| 5432 | postgres | PostgreSQL (прямой доступ) |
| 6379 | redis | Redis (прямой доступ) |

---

## Частые проблемы

### ❌ "address already in use" — порт 5432 или 6379 занят

Чаще всего это старые контейнеры в состоянии `Created`/`Exited`, которые держат
сетевые ресурсы Docker. Проверить:
```bash
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

**Решение — очистить и перезапустить:**
```bash
# Удалить все контейнеры проекта (включая остановленные)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down --remove-orphans

# Запустить заново
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

Если ошибка повторяется — принудительная очистка:
```bash
docker rm -f expenses_postgres expenses_redis expenses_frontend \
             expenses_api expenses_bot expenses_adminer 2>/dev/null
docker network prune -f
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

Если порт занят **системным** сервисом (не Docker):
```bash
# Проверить
ss -tlnp | grep -E "5432|6379"

# macOS
brew services stop postgresql
brew services stop redis

# Linux
sudo systemctl stop postgresql redis
```

### ❌ `api` не стартует — "could not connect to server"
PostgreSQL ещё не готов. Подождите 10–15 секунд и перезапустите:
```bash
docker-compose restart api bot
```

### ❌ `alembic upgrade head` — ошибка подключения
Убедитесь что postgres запущен:
```bash
docker-compose ps postgres
```

### ❌ Бот не отвечает
Проверьте `BOT_TOKEN` в `.env` и логи:
```bash
docker-compose logs bot
```
