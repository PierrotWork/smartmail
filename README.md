# SmartMail Campaigns

Веб-приложение для сегментированных email-рассылок с интеллектуальным скорингом клиентской базы.

## Что это

Приложение получает клиентскую базу из внешнего CRM через API, оценивает каждого клиента по релевантности продукту с помощью подключаемого алгоритма скоринга, и позволяет маркетологам собирать сегментированные email-рассылки и отправлять их через выбранный ESP (Unisender / SendGrid / Mailgun / SMTP).

## Архитектура (кратко)

- **Frontend:** React + TypeScript + Vite (SPA)
- **Backend:** Python + FastAPI (модульный монолит)
- **База данных:** PostgreSQL 15
- **Кэш и очереди:** Redis + Celery
- **Фоновые задачи:** воркеры для синхронизации, скоринга, отправки
- **Интеграции:** CRM Adapter, ESP Adapter, Scoring Adapter — все через единые интерфейсы

Подробнее — см. `docs/ARCHITECTURE.md`.

## Быстрый старт (локально)

Требуется: Docker Desktop.

```bash
cp .env.example .env
# при необходимости отредактировать .env

docker compose up -d
```

После запуска:

- Backend API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- Frontend: http://localhost:5173
- PostgreSQL: localhost:5432 (см. .env)
- Redis: localhost:6379

## Структура репозитория

```
smartmail/
├── backend/            FastAPI-приложение, воркеры, миграции
│   ├── app/
│   │   ├── core/       Кросс-модульная инфраструктура (безопасность, логи)
│   │   ├── modules/    Бизнес-модули (auth, clients, campaigns, ...)
│   │   └── workers/    Celery-задачи
│   └── alembic/        Миграции БД
├── frontend/           React SPA
├── docs/               Документация архитектуры
└── docker-compose.yml
```

## Разработка

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1     # Windows PowerShell
pip install -e ".[dev]"

# миграции
alembic upgrade head

# локальный запуск (без Docker)
uvicorn app.main:app --reload

# запуск воркеров
celery -A app.workers.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Первый пуш в GitHub

```bash
cd smartmail
git init
git add .
git commit -m "initial scaffold"
git branch -M main
git remote add origin git@github.com:<username>/smartmail.git
git push -u origin main
```

⚠️ Перед первым пушем **обязательно проверь**, что `.env` не попал в staged-файлы:

```bash
git status
git ls-files | grep -i env    # должен показать только .env.example
```

## Деплой на VPS

Полная инструкция — в `DEPLOYMENT.md`. Кратко:

1. Настроить VPS (Docker, firewall, пользователь `deploy`)
2. Клонировать репо в `/opt/smartmail`
3. Скопировать `.env.example` → `.env`, заполнить продовыми значениями
4. Запустить: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
5. Настроить GitHub Actions секреты для автодеплоя

## Дорожная карта

- [x] Sprint 0 — скелет проекта, инфраструктура
- [ ] Sprint 1-2 — auth, базовое API, деплой
- [ ] Sprint 3-4 — CRM Adapter, синхронизация, экран клиентов
- [ ] Sprint 5-6 — шаблоны и сегментация
- [ ] Sprint 7-8 — ESP Adapter, отправка, экран рассылок
- [ ] Sprint 9 — Scoring Adapter (заглушка)
- [ ] Sprint 10 — вебхуки ESP, аналитика
- [ ] Sprint 11 — реальный алгоритм скоринга
- [ ] Sprint 12 — RBAC, аудит, нагрузка
- [ ] Sprint 13 — production-запуск
