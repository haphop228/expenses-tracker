#!/bin/sh

set -eu

NGINX_CONTAINER="expenses_nginx"

if [ "$(docker inspect --format '{{.State.Running}}' "$NGINX_CONTAINER")" != "true" ]; then
    echo "Контейнер $NGINX_CONTAINER не запущен" >&2
    exit 1
fi

docker exec "$NGINX_CONTAINER" nginx -t
docker exec "$NGINX_CONTAINER" nginx -s reload

