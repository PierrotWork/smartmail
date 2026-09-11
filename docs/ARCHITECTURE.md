# Архитектура

Актуальный документ по архитектуре системы: [../../asgardcentr-seo-report.md] — нет, здесь свежая версия.

## Общие принципы

Приложение спроектировано как **модульный монолит** с чёткими границами модулей. Это компромисс между скоростью разработки (не надо чинить сеть между сервисами) и готовностью к масштабированию (модули можно выделить в отдельные сервисы, когда объём вырастет).

Ключевые решения:

1. **Stateless backend** — любой инстанс FastAPI обрабатывает любой запрос. Состояние живёт в PostgreSQL и Redis.
2. **Асинхронная обработка** — всё, что дольше 1 секунды, уходит в Celery-очередь.
3. **Адаптерный слой** — CRM, ESP и алгоритм скоринга подключаются через интерфейсы (Protocol в Python), что позволяет менять поставщиков без переписывания бизнес-логики.
4. **Freeze segment** — при запуске рассылки мы делаем снимок получателей (материализуем в `campaign_recipients`). Дальнейшие изменения базы не влияют на рассылку в процессе.

## Границы модулей

```
backend/app/modules/
├── auth/          Пользователи, роли, JWT, аудит
├── clients/       Клиентская база, фильтры, история скоров
├── templates/     HTML/text шаблоны, Jinja-рендер, версионирование
├── campaigns/     Рассылки, снимки сегментов, статистика
└── integrations/
    ├── crm/       Адаптер к внешней CRM (Protocol + реализация)
    ├── esp/       Адаптер к провайдеру отправки писем
    └── scoring/   Адаптер к алгоритму скоринга (mock + http)
```

Каждый модуль содержит: `models.py` (SQLAlchemy), `schemas.py` (Pydantic), `service.py` (бизнес-логика), `router.py` (FastAPI-эндпойнты).

## Потоки данных

### Синхронизация клиентов

```
Celery Beat (каждые N минут) ──▶ sync_all_clients task
                                        │
                                        ▼
                              GenericCRMAdapter.fetch_clients()  ── (async iterator)
                                        │
                                        ▼
                              clients_service.upsert_from_external(batch)
                                        │
                                        ▼
                              rescore_all_clients.delay()
```

### Скоринг

```
sync_tasks / cron / ручной запрос
        │
        ▼
score_tasks.rescore_all_clients()
        │
        ▼
ScoringAdapter.score(batch) ── возвращает [ScoreResult(...)]
        │
        ▼
UPDATE clients SET current_score = ... + INSERT INTO score_history
```

### Отправка рассылки

```
User: POST /campaigns/{id}/send
        │
        ▼
campaigns_service.start_campaign()
        │  ├─► freeze_segment() — материализация CampaignRecipient
        │  └─► status = SENDING
        ▼
Celery: send_campaign.delay(campaign_id)
        │
        ▼
send_tasks._send() ── батчами по 100
        │
        ▼
ESPAdapter.send_batch(messages)
        │
        ▼
UPDATE campaign_recipients SET status/sent_at/...
```

### Вебхуки ESP (TODO)

```
ESP (SendGrid/Unisender/…) ── POST /api/v1/webhooks/esp/{provider}
        │
        ▼
Проверка подписи → задача в очередь webhooks
        │
        ▼
UPDATE campaign_recipients + агрегированные метрики
```

## Модель данных

```
users ────────────┐
                  │ created_by
                  ▼
campaigns ──────► email_templates
    │
    ▼
campaign_recipients ──── client_id ────► clients ──── has-many ───► score_history
```

## Технологии

| Слой | Стек |
|---|---|
| Frontend | React 18 + TypeScript + Vite + Mantine UI + TanStack Query |
| Backend | Python 3.11 + FastAPI + SQLAlchemy 2 |
| DB | PostgreSQL 15 (JSONB для гибких атрибутов и фильтров) |
| Кэш / очереди | Redis + Celery + Celery Beat |
| Отправка | SMTP (dev) + Unisender/SendGrid (prod) через ESPAdapter |
| Аутентификация | JWT (access 15 мин + refresh 7 дней) |
| Миграции | Alembic |

## Развёртывание

**Разработка:** `docker compose up` — поднимает postgres, redis, mailhog (SMTP-ловушка), backend, worker, beat, frontend.

**Прод (минимум):**
- 1× nginx (TLS) → backend
- 2× backend API
- 1× celery worker (несколько очередей)
- 1× celery beat
- 1× postgres (с бэкапами)
- 1× redis

## Что ещё нужно доделать (по этапам)

- [ ] Реальный CRM adapter под конкретный API вашей CRM
- [ ] UnisenderAdapter / SendGridAdapter в `integrations/esp/`
- [ ] Вебхуки ESP: приёмник + обработка событий
- [ ] Реальный алгоритм скоринга (заменит `MockScoringAdapter`)
- [ ] UI: конструктор сегмента с фильтрами, WYSIWYG-редактор шаблонов, мастер создания рассылки
- [ ] Обработка отписок: страница `/unsubscribe?token=...`
- [ ] Аудит-лог: middleware, пишущий действия в `audit_log`
- [ ] Тесты: unit + integration + e2e
