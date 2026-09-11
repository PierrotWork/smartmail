# Деплой на VPS

Пошаговая инструкция запуска SmartMail Campaigns на продакшене.

## 0. Что понадобится

- VPS с Ubuntu 22.04+ или Debian 12+ (минимум 2 vCPU, 4 GB RAM, 40 GB диска)
- Домен (например, `smartmail.example.com`), у которого A-запись указывает на IP VPS
- Аккаунт GitHub с приватным репозиторием
- SSH-доступ к VPS

## 1. Подготовка VPS

### 1.1. Обновление и базовые пакеты

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ufw fail2ban htop
```

### 1.2. Firewall — открыть только 22, 80, 443

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status
```

### 1.3. Docker + Docker Compose

```bash
# Официальный installer от Docker
curl -fsSL https://get.docker.com | sudo sh

# Добавить себя в группу docker, чтобы не писать sudo
sudo usermod -aG docker $USER
# перелогиниться (exit и заново по SSH)

docker --version
docker compose version
```

### 1.4. Отдельный пользователь для деплоя (рекомендуется)

```bash
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy

# SSH-ключ для GitHub Actions
sudo -u deploy mkdir -p /home/deploy/.ssh
sudo -u deploy chmod 700 /home/deploy/.ssh
# добавить свой публичный ключ в authorized_keys
sudo -u deploy nano /home/deploy/.ssh/authorized_keys
sudo -u deploy chmod 600 /home/deploy/.ssh/authorized_keys
```

## 2. Клонирование репозитория

```bash
sudo mkdir -p /opt/smartmail
sudo chown deploy:deploy /opt/smartmail
cd /opt/smartmail

# Через SSH — если репо приватный
git clone git@github.com:<username>/smartmail.git .
```

Для приватного репо нужно либо:
- Добавить deploy key в настройках репозитория (Settings → Deploy keys), или
- Сгенерировать personal access token и клонировать через HTTPS

## 3. Настройка `.env`

```bash
cp .env.example .env
nano .env
```

Обязательно измени:

```env
APP_ENV=production
APP_DEBUG=false

# Сгенерируй командой: python3 -c "import secrets; print(secrets.token_urlsafe(48))"
APP_SECRET_KEY=<длинный случайный ключ>

APP_DOMAIN=smartmail.example.com

# База — придумай сложный пароль
POSTGRES_PASSWORD=<сильный пароль>
DATABASE_URL=postgresql+psycopg://smartmail:<сильный пароль>@postgres:5432/smartmail

CORS_ORIGINS=https://smartmail.example.com
VITE_API_BASE_URL=/

# CRM
CRM_API_BASE_URL=https://your-crm.example.com/api/v1
CRM_API_KEY=<реальный ключ>

# ESP — например SendGrid
ESP_PROVIDER=sendgrid
SENDGRID_API_KEY=<реальный ключ>
SMTP_FROM_EMAIL=noreply@smartmail.example.com
SMTP_FROM_NAME=SmartMail

# Скоринг
SCORING_PROVIDER=mock   # или http, когда алгоритм будет готов
```

Проверь права:
```bash
chmod 600 .env
```

## 4. Первый запуск

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Дождись, пока контейнеры поднимутся, затем прогони миграции и создай администратора:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    exec backend alembic upgrade head

docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    exec backend python scripts/create_admin.py admin@example.com <пароль> "Admin"
```

Проверь работу:

```bash
curl https://smartmail.example.com/health
# → {"status":"ok","version":"0.1.0","env":"production"}
```

Caddy выпустит Let's Encrypt-сертификат автоматически при первом обращении.

## 5. Автодеплой через GitHub Actions

### 5.1. Секреты в репозитории

`Settings → Secrets and variables → Actions → New repository secret`:

| Имя | Значение |
|---|---|
| `VPS_HOST` | IP или домен VPS |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | Приватный SSH-ключ (см. ниже) |
| `VPS_APP_PATH` | `/opt/smartmail` |

### 5.2. SSH-ключ для деплоя

На локальной машине:
```bash
ssh-keygen -t ed25519 -f smartmail_deploy -C "github-actions"
# получишь smartmail_deploy (приватный) и smartmail_deploy.pub (публичный)
```

- Публичный ключ (`.pub`) добавь в `/home/deploy/.ssh/authorized_keys` на VPS
- Приватный (`smartmail_deploy` без расширения) целиком скопируй в GitHub-секрет `VPS_SSH_KEY`

### 5.3. Как работает деплой

При пуше в `main`:
1. `ci.yml` — линтеры, типы, сборка
2. `deploy.yml` — SSH на VPS → `git pull` → пересборка контейнеров → миграции

## 6. Бэкапы Postgres

Ежедневный дамп базы + ротация 30 дней. Добавь в crontab пользователя `deploy`:

```bash
crontab -e
```

```cron
0 3 * * * cd /opt/smartmail && docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T postgres pg_dump -U smartmail smartmail | gzip > /opt/backups/smartmail-$(date +\%Y-\%m-\%d).sql.gz
0 4 * * * find /opt/backups -name "smartmail-*.sql.gz" -mtime +30 -delete
```

Не забудь:
```bash
sudo mkdir -p /opt/backups && sudo chown deploy /opt/backups
```

Настоятельно рекомендую параллельно синхронизировать `/opt/backups` куда-нибудь наружу (rclone → S3, отдельный сервер).

## 7. Мониторинг (минимум)

Простейший чек — cron с алертом в Telegram:

```bash
*/5 * * * * curl -sf https://smartmail.example.com/health >/dev/null || curl -s "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>&text=SmartMail%20DOWN"
```

Для «взрослого» мониторинга подключай Uptime Kuma, Prometheus + Grafana или сторонний сервис (Better Stack, UptimeRobot).

## 8. Обновление вручную (если Actions не сработали)

```bash
ssh deploy@your-vps
cd /opt/smartmail
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend alembic upgrade head
```

## 9. Откат на предыдущую версию

```bash
cd /opt/smartmail
git log --oneline -5      # найди коммит
git checkout <sha>
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Если проблема в миграции — откатись через `alembic downgrade -1`.

## 10. Чек-лист безопасности

- [ ] `.env` не в git и chmod 600
- [ ] `APP_SECRET_KEY` — не значение по умолчанию
- [ ] `POSTGRES_PASSWORD` — не значение по умолчанию
- [ ] Firewall открыт только для 22, 80, 443
- [ ] SSH по ключу (запрещён вход по паролю в `/etc/ssh/sshd_config`: `PasswordAuthentication no`)
- [ ] fail2ban включён
- [ ] Регулярные обновления (`unattended-upgrades`)
- [ ] Регулярный внешний бэкап базы
- [ ] Настроен мониторинг доступности
