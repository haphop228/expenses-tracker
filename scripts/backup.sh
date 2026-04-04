#!/bin/bash
# Скрипт создания бэкапа PostgreSQL
# Запуск: ./scripts/backup.sh [daily|weekly|monthly]

set -e

BACKUP_TYPE=${1:-daily}
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M")
FILENAME="backup_${TIMESTAMP}.sql.gz"

case "$BACKUP_TYPE" in
    daily)   BACKUP_DIR="./backups/daily";   KEEP=7  ;;
    weekly)  BACKUP_DIR="./backups/weekly";  KEEP=4  ;;
    monthly) BACKUP_DIR="./backups/monthly"; KEEP=3  ;;
    *)
        echo "❌ Неизвестный тип бэкапа: $BACKUP_TYPE"
        echo "   Использование: $0 [daily|weekly|monthly]"
        exit 1
        ;;
esac

echo "💾 Создание $BACKUP_TYPE бэкапа: $FILENAME"

# Создать директорию если не существует
mkdir -p "$BACKUP_DIR"

# Загрузить переменные окружения
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Создать бэкап
docker-compose exec -T postgres pg_dump \
    -U "${POSTGRES_USER:-expenses_user}" \
    "${POSTGRES_DB:-expenses}" \
    | gzip > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -sh "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "✅ Бэкап создан: ${BACKUP_DIR}/${FILENAME} (${SIZE})"

# Ротация: оставить только последние $KEEP бэкапов
cd "$BACKUP_DIR"
COUNT=$(ls -1 backup_*.sql.gz 2>/dev/null | wc -l)
if [ "$COUNT" -gt "$KEEP" ]; then
    ls -t backup_*.sql.gz | tail -n +$((KEEP + 1)) | xargs rm -f
    echo "🗑️  Удалены старые бэкапы (оставлено: $KEEP)"
fi

echo "✅ Готово"
