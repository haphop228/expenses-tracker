# Развёртывание в production

Текущая production-инсталляция находится в `/root/expenses-tracker` и управляется
через `docker-compose` 1.29.2. Контейнер `telegram-proxy` относится к другому
проекту: команды из этого документа его не изменяют.

## Обновление кода

Сначала опубликуйте локальные изменения:

```bash
git status --short
git diff --check
git add DEPLOYMENT.md GETTING_STARTED.md README.md \
  scripts/configure_certbot_webroot.sh \
  scripts/reload_nginx_after_certbot.sh
git commit -m "configure certbot webroot renewal"
git push origin main
```

Перед обновлением убедитесь, что в серверном checkout нет незакоммиченных правок:

```bash
sudo git -C /root/expenses-tracker status --short --branch
```

После публикации изменений в `origin/main`:

```bash
sudo git -C /root/expenses-tracker pull --ff-only origin main
sudo sh -c 'cd /root/expenses-tracker && docker-compose config --quiet'
sudo sh -c 'cd /root/expenses-tracker && docker-compose up -d --build'
sudo sh -c 'cd /root/expenses-tracker && docker-compose ps'
```

`docker-compose up -d --build` пересобирает образы приложения и пересоздаёт
только нужные сервисы Compose-проекта `expenses-tracker`. Не используйте
`docker-compose down -v`: эта команда удалит volumes PostgreSQL и Redis.
Обычный `docker-compose restart` недостаточен для изменений кода, потому что
он не пересобирает Docker images.

## Настройка автоматического продления TLS

Nginx отдаёт ACME HTTP-01 challenge из
`nginx/certbot-webroot/.well-known/acme-challenge`. Скрипт ниже:

1. проверяет доступность webroot снаружи по HTTP;
2. безопасно тестирует новую конфигурацию через `certbot reconfigure`;
3. сохраняет authenticator `webroot` и deploy hook;
4. продлевает сертификат, если он уже подлежит продлению;
5. включает `certbot.timer` и проверяет HTTPS health endpoint.

Для текущего домена:

```bash
sudo /root/expenses-tracker/scripts/configure_certbot_webroot.sh \
  hophop228-expences.duckdns.org
```

После каждого успешного будущего продления Certbot вызовет
`scripts/reload_nginx_after_certbot.sh`. Hook сначала проверит конфигурацию
Nginx, затем перечитает сертификат без остановки контейнера.

Настройку можно проверить командами:

```bash
sudo systemctl status certbot.timer --no-pager
sudo certbot renew --dry-run
openssl s_client \
  -connect hophop228-expences.duckdns.org:443 \
  -servername hophop228-expences.duckdns.org </dev/null 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates
curl --fail --show-error --silent \
  https://hophop228-expences.duckdns.org/health
```

На текущей ВМ также нужно один раз удалить из `/etc/crontab` ошибочную строку,
которая начинается с `echo "0 3 * * * root certbot renew`. Это не cron-задание;
автоматический запуск обеспечивает штатный `certbot.timer`.

## TLS-only раскатка

Для добавленных TLS-скриптов не требуется пересобирать или перезапускать все
контейнеры. Достаточно получить код и запустить настройку:

```bash
sudo git -C /root/expenses-tracker pull --ff-only origin main
sudo /root/expenses-tracker/scripts/configure_certbot_webroot.sh \
  hophop228-expences.duckdns.org
```

При успешном выпуске нового сертификата reload затронет только
`expenses_nginx`; `telegram-proxy` не затрагивается.
