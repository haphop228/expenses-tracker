# 📖 GETTING STARTED — Первый запуск на сервере

Этот гайд описывает что делать **после** того как все контейнеры подняты и работают.

---

## Содержание

1. [Проверить что всё запущено](#1-проверить-что-всё-запущено)
2. [Создать администратора](#2-создать-администратора)
3. [Войти в панель администратора](#3-войти-в-панель-администратора)
4. [Создать группу](#4-создать-группу)
5. [Создать инвайт-код и зарегистрировать пользователя](#5-создать-инвайт-код-и-зарегистрировать-пользователя)
6. [Привязать Telegram-аккаунт](#6-привязать-telegram-аккаунт)
7. [Начать вести расходы](#7-начать-вести-расходы)
8. [Полезные команды](#8-полезные-команды)

---

## 1. Проверить что всё запущено

```bash
docker-compose ps
```

Все сервисы должны быть в статусе `Up`:

```
expenses_postgres   Up (healthy)
expenses_redis      Up (healthy)
expenses_api        Up (healthy)
expenses_bot        Up
expenses_frontend   Up
expenses_nginx      Up
```

Если какой-то сервис не запущен — посмотреть логи:

```bash
docker-compose logs <имя_сервиса>
# Например:
docker-compose logs api
docker-compose logs nginx
```

> 💡 **Таблицы в БД создаются автоматически** при первом старте API-сервиса.
> В логах будет: `БД: таблицы проверены/созданы`

---

## 2. Создать администратора

```bash
docker-compose exec api python scripts/create_admin.py \
  --login admin \
  --password ВашНадёжныйПароль123
```

> 💡 Логин и пароль — только для входа в панель администратора.
> Пароль должен быть надёжным — это единственная защита admin-панели.

Пример:
```bash
docker-compose exec api python scripts/create_admin.py \
  --login admin \
  --password MySecretAdminPass2024!
```

---

## 3. Войти в панель администратора

Admin-панель доступна **только через SSH tunnel** — она не открыта в интернет.

### Шаг 3.1 — Открыть SSH tunnel

На **вашем локальном компьютере** выполните:

```bash
ssh -L 8080:127.0.0.1:8080 user@ваш_сервер -N
```

Замените `user@ваш_сервер` на реальные данные, например:
```bash
ssh -L 8080:127.0.0.1:8080 root@213.165.213.170 -N
```

Оставьте этот терминал открытым — tunnel работает пока он запущен.

### Шаг 3.2 — Открыть в браузере

Перейдите по адресу: **http://localhost:8080/admin/login**

Введите логин и пароль, созданные на шаге 2.

---

## 4. Создать группу

В панели администратора:

1. Нажмите кнопку **"+ Создать группу"**
2. Введите название группы (например: "Семья Ивановых")
3. Нажмите **"Создать"**

Группа появится в списке.

---

## 5. Создать инвайт-код и зарегистрировать пользователя

### Шаг 5.1 — Создать инвайт-код

В панели администратора:

1. Найдите нужную группу в списке
2. Нажмите кнопку **"Инвайт"** напротив группы
3. Скопируйте полученный код (действует 7 дней)

### Шаг 5.2 — Зарегистрироваться

Пользователь открывает сайт: **https://ваш_домен/register**

Вводит:
- Инвайт-код (полученный на шаге 5.1)
- Имя
- Логин (для входа на сайт)
- Пароль

После регистрации пользователь автоматически входит в систему.

---

## 6. Привязать Telegram-аккаунт

Это нужно чтобы пользоваться Telegram-ботом для добавления расходов.

### Шаг 6.1 — Получить код привязки

Пользователь заходит на сайт → **Настройки** → вкладка **"Telegram"** → нажимает **"Получить код привязки"**.

Появится команда вида:
```
/link ABCD1234
```

### Шаг 6.2 — Отправить команду боту

Пользователь открывает Telegram, находит бота (по имени из BotFather) и отправляет команду:
```
/link ABCD1234
```

Бот ответит: **"✅ Аккаунт успешно привязан!"**

---

## 7. Начать вести расходы

### Через веб-интерфейс

Открыть **https://ваш_домен** → войти → использовать раздел **"Расходы"**.

### Через Telegram-бота

Написать боту в Telegram. Доступные команды:

- `/start` — главное меню
- `/menu` — открыть меню
- Нажать **"➕ Добавить трату"** → выбрать категорию → ввести сумму

Формат ввода суммы:
```
150          # просто сумма
150 кофе     # сумма с комментарием
150, кофе    # тоже работает
```

---

## 8. Полезные команды

### Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Только API
docker-compose logs -f api

# Только бот
docker-compose logs -f bot

# Только nginx
docker-compose logs -f nginx
```

### Перезапуск сервисов

```bash
# Перезапустить API
docker-compose restart api

# Перезапустить бота
docker-compose restart bot

# Перезапустить nginx (с применением нового конфига)
docker exec expenses_nginx /bin/sh -c \
  "envsubst '\$DOMAIN' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf && nginx -s reload"
```

### Обновление приложения

```bash
# Получить новый код
git pull

# Пересобрать и перезапустить
docker-compose up --build -d
```

> 💡 Таблицы БД обновляются автоматически при старте API (через `Base.metadata.create_all`).
> Alembic-миграции не используются.

### Создать дополнительного администратора

```bash
docker-compose exec api python scripts/create_admin.py \
  --login admin2 \
  --password ДругойПароль456
```

### Резервная копия БД

```bash
docker-compose exec postgres pg_dump \
  -U ${POSTGRES_USER:-expenses_user} \
  ${POSTGRES_DB:-expenses} > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Проверка здоровья сервисов

```bash
# Статус всех контейнеров
docker-compose ps

# Health API
curl -s https://ваш_домен/health | python3 -m json.tool

# Health через SSH tunnel (если открыт)
curl -s http://localhost:8080/health | python3 -m json.tool
```

---

## Структура доступа

| Что | Адрес | Кто имеет доступ |
|-----|-------|-----------------|
| Веб-приложение | `https://ваш_домен/` | Все зарегистрированные пользователи |
| API документация | `https://ваш_домен/api/docs` | Все (только чтение) |
| Admin-панель | `http://localhost:8080/admin/` | Только через SSH tunnel |
| Admin API | `http://localhost:8080/api/v1/admin/` | Только через SSH tunnel |

> ⚠️ `/admin` и `/api/v1/admin/` заблокированы в публичном nginx — возвращают 403.
> Доступ только через SSH tunnel на порт 8080.

---

## Частые вопросы

### ❓ Забыл пароль администратора

Создать нового администратора с другим логином:
```bash
docker-compose exec api python scripts/create_admin.py \
  --login admin_new \
  --password НовыйПароль789
```

Или сбросить пароль напрямую в БД:
```bash
docker-compose exec api python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.config import settings
from core.security import hash_password
from sqlalchemy import update
from models.models import Admin

async def reset():
    engine = create_async_engine(settings.DATABASE_URL)
    async with async_sessionmaker(engine)() as session:
        await session.execute(
            update(Admin).where(Admin.login == 'admin').values(
                password_hash=hash_password('НовыйПароль')
            )
        )
        await session.commit()
    print('Пароль сброшен')

asyncio.run(reset())
"
```

### ❓ Пользователь не может войти

1. Проверить что пользователь зарегистрирован (через admin-панель → группа → участники)
2. Проверить логи API: `docker-compose logs api | grep -i error`

### ❓ Бот не отвечает

```bash
# Проверить логи бота
docker-compose logs bot | tail -20

# Проверить что BOT_TOKEN правильный в .env
grep BOT_TOKEN .env
```

### ❓ Инвайт-код не работает

Инвайт-коды действуют **7 дней**. Создайте новый через admin-панель.

### ❓ `password authentication failed for user "expenses_user"`

PostgreSQL инициализируется **один раз** при первом запуске с паролем из `.env`.
Если `.env` менялся после этого — пароль в БД остался старым.

Сбросить пароль без потери данных:
```bash
docker exec expenses_postgres psql -U expenses_user -d expenses -c \
  "ALTER USER expenses_user WITH PASSWORD 'ваш_пароль_из_env';"
```

После этого перезапустить API:
```bash
docker-compose restart api
```

> ⚠️ Не используйте `docker-compose down -v` — флаг `-v` удаляет тома с данными БД.
> Обычный `docker-compose down` + `docker-compose up -d` тома не трогает.
