#!/bin/bash
# Скрипт восстановления PostgreSQL из бэкапа
# Запуск: ./scripts/restore.sh <backup_file.sql.gz>

set -e

if [ -z "$1" ]; then
    echo "❌ Укажите файл бэкапа"
    echo "   Использование: $0 <backup_file.sql.gz>"
    echo ""
    echo "   Доступные бэкапы:"
    find ./backups -name "*.sql.gz" -type f | sort -r | head -20
    exit 1
fi

BACKUP_FILE=$1

if [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ Файл не найден: $BACKUP_FILE"
    exit 1
fi

echo "⚠️  ВНИМАНИЕ: Восстановление полностью заменит текущую базу данных!"
echo "   Файл: $BACKUP_FILE"
echo ""
read -p "Продолжить? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Восстановление отменено"
    exit 0
fi

# Загрузить переменные окружения
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

echo "🛑 Останавливаю API и Bot..."
docker-compose stop api bot

echo "🔄 Восстанавливаю базу данных..."
gunzip < "$BACKUP_FILE" | docker-compose exec -T postgres psql \
    -U "${POSTGRES_USER:-expenses_user}" \
    "${POSTGRES_DB:-expenses}"

echo "🚀 Запускаю API и Bot..."
docker-compose start api bot

echo "✅ Восстановление завершено успешно!"
echo "   Восстановлено из: $BACKUP_FILE"
