#!/bin/bash
# Скрипт инициализации PostgreSQL
# Выполняется автоматически при первом запуске контейнера postgres
# Переменные POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB доступны из окружения контейнера

set -e

echo "=== PostgreSQL init: явная установка пароля для TCP-подключений ==="

# Экранируем одинарные кавычки в пароле (заменяем ' на '')
ESCAPED_PASSWORD="${POSTGRES_PASSWORD//\'/\'\'}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    ALTER USER "$POSTGRES_USER" WITH PASSWORD '$ESCAPED_PASSWORD';
EOSQL

echo "=== PostgreSQL init: пароль установлен ==="
