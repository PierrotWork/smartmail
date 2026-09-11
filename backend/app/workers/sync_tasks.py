"""Задачи синхронизации клиентской базы с внешним CRM."""

import asyncio
import logging

from app.database import SessionLocal
from app.modules.clients import service as clients_service
from app.modules.integrations.crm.adapter import get_crm_adapter
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)


@celery_app.task(name="app.workers.sync_tasks.sync_all_clients", bind=True, max_retries=3)
def sync_all_clients(self) -> dict:
    """Полная/инкрементальная синхронизация клиентов из CRM."""
    try:
        return asyncio.run(_sync())
    except Exception as exc:  # noqa: BLE001
        log.exception("Sync failed, will retry")
        raise self.retry(exc=exc, countdown=60) from exc


async def _sync() -> dict:
    created_total = 0
    updated_total = 0
    batches = 0

    adapter = get_crm_adapter()
    async with adapter:
        async for batch in adapter.fetch_clients():
            batches += 1
            with SessionLocal() as db:
                created, updated = clients_service.upsert_from_external(db, batch)
                created_total += created
                updated_total += updated

    # После синхронизации ставим задачу пересчёта скоров
    from app.workers.score_tasks import rescore_all_clients

    rescore_all_clients.delay()

    return {"batches": batches, "created": created_total, "updated": updated_total}
