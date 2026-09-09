#!/bin/sh

set -eu

NGINX_CONTAINER="expenses_nginx"

if [ "$(docker inspect --format '{{.State.Running}}' "$NGINX_CONTAINER")" != "true" ]; then
    echo "Контейнер $NGINX_CONTAINER не запущен" >&2
    exit 1
fi

if ! nginx_test_output="$(docker exec "$NGINX_CONTAINER" nginx -t 2>&1)"; then
    printf '%s\n' "$nginx_test_output" >&2
    exit 1
fi

if ! nginx_reload_output="$(docker exec "$NGINX_CONTAINER" nginx -s reload 2>&1)"; then
    printf '%s\n' "$nginx_reload_output" >&2
    exit 1
fi
