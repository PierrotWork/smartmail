"""Celery-приложение и расписание периодических задач."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

# ВАЖНО: подцепить ВСЕ модели, чтобы SQLAlchemy metadata знала про все таблицы
# и внешние ключи между модулями резолвились (иначе воркер падает на первом же
# commit() c NoReferencedTableError). Без routers мы теряем неявные импорты,
# которые есть в API-процессе через main.py.
from app.modules.auth import models as _auth_models  # noqa: F401
from app.modules.campaigns import models as _campaigns_models  # noqa: F401
from app.modules.clients import models as _clients_models  # noqa: F401
from app.modules.settings import models as _settings_models  # noqa: F401
from app.modules.templates import models as _templates_models  # noqa: F401

celery_app = Celery(
    "smartmail",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.sync_tasks",
        "app.workers.score_tasks",
        "app.workers.send_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_default_queue="default",
    task_routes={
        "app.workers.sync_tasks.*": {"queue": "sync"},
        "app.workers.score_tasks.*": {"queue": "score"},
        "app.workers.send_tasks.*": {"queue": "send"},
    },
    # Периодические задачи (celery beat)
    beat_schedule={
        "sync-crm-clients": {
            "task": "app.workers.sync_tasks.sync_all_clients",
            "schedule": crontab(minute=f"*/{settings.crm_sync_interval_minutes}"),
        },
        "rescore-clients-nightly": {
            "task": "app.workers.score_tasks.rescore_all_clients",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
