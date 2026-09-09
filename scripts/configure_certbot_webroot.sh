#!/usr/bin/env bash

set -Eeuo pipefail

readonly NGINX_CONTAINER="expenses_nginx"

usage() {
    cat <<'EOF'
Использование:
  sudo ./scripts/configure_certbot_webroot.sh <domain>

Пример:
  sudo ./scripts/configure_certbot_webroot.sh example.com
EOF
}

fail() {
    echo "Ошибка: $*" >&2
    exit 1
}

if [[ ${EUID} -ne 0 ]]; then
    fail "скрипт должен быть запущен через sudo"
fi

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi

readonly TLS_DOMAIN="$1"

if [[ ! ${TLS_DOMAIN} =~ ^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$ ]]; then
    fail "некорректное доменное имя: ${TLS_DOMAIN}"
fi

for required_command in certbot curl docker openssl systemctl; do
    command -v "${required_command}" >/dev/null 2>&1 \
        || fail "не найдена команда ${required_command}"
done

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly WEBROOT_PATH="${PROJECT_DIR}/nginx/certbot-webroot"
readonly CHALLENGE_DIR="${WEBROOT_PATH}/.well-known/acme-challenge"
readonly CERTIFICATE_PATH="/etc/letsencrypt/live/${TLS_DOMAIN}/fullchain.pem"
readonly DEPLOY_HOOK="${SCRIPT_DIR}/reload_nginx_after_certbot.sh"

[[ -f ${CERTIFICATE_PATH} ]] || fail \
    "сертификат ${CERTIFICATE_PATH} не найден; сначала нужен первичный выпуск сертификата"
[[ -x ${DEPLOY_HOOK} ]] || fail "deploy hook не исполняемый: ${DEPLOY_HOOK}"

if [[ $(docker inspect --format '{{.State.Running}}' "${NGINX_CONTAINER}" 2>/dev/null) != true ]]; then
    fail "контейнер ${NGINX_CONTAINER} не запущен"
fi

docker exec "${NGINX_CONTAINER}" nginx -t

install -d -m 0755 "${CHALLENGE_DIR}"

probe_file="$(mktemp "${CHALLENGE_DIR}/expenses-certbot-probe.XXXXXX")"
readonly probe_file
readonly probe_name="$(basename -- "${probe_file}")"
readonly probe_value="expenses-certbot-webroot-ok"
trap 'rm -f -- "${probe_file}"' EXIT

printf '%s\n' "${probe_value}" >"${probe_file}"
chmod 0644 "${probe_file}"

served_probe="$(curl --fail --silent --show-error --max-time 15 \
    "http://${TLS_DOMAIN}/.well-known/acme-challenge/${probe_name}")" \
    || fail "Nginx не отдаёт файлы из ACME webroot"

if [[ ${served_probe} != "${probe_value}" ]]; then
    fail "ответ ACME webroot не совпал с тестовым значением"
fi

rm -f -- "${probe_file}"
trap - EXIT

echo "ACME webroot доступен. Перевожу сертификат ${TLS_DOMAIN} на webroot..."
certbot reconfigure \
    --cert-name "${TLS_DOMAIN}" \
    --webroot \
    --webroot-path "${WEBROOT_PATH}" \
    --deploy-hook "${DEPLOY_HOOK}" \
    --run-deploy-hooks

echo "Проверяю необходимость реального продления..."
certbot renew --cert-name "${TLS_DOMAIN}"

systemctl enable --now certbot.timer

echo "Текущий сертификат:"
openssl x509 -in "${CERTIFICATE_PATH}" \
    -noout -subject -issuer -dates -ext subjectAltName

echo "Проверяю HTTPS после настройки..."
curl --fail --silent --show-error --max-time 15 \
    --output /dev/null "https://${TLS_DOMAIN}/health"

echo "Готово: webroot-продление настроено, HTTPS health check успешен."
