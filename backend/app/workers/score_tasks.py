"""Задачи скоринга клиентов."""

import logging

from sqlalchemy import select

from app.database import SessionLocal
from app.modules.clients.models import Client, ScoreHistory
from app.modules.integrations.scoring.mock import get_scoring_adapter
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

BATCH_SIZE = 500


@celery_app.task(name="app.workers.score_tasks.rescore_all_clients")
def rescore_all_clients() -> dict:
    """Пересчитать скоры всех активных клиентов."""
    adapter = get_scoring_adapter()
    scored_total = 0
    batches = 0

    with SessionLocal() as db:
        stmt = select(Client).where(Client.is_unsubscribed.is_(False))
        offset = 0
        while True:
            batch = list(db.scalars(stmt.limit(BATCH_SIZE).offset(offset)).all())
            if not batch:
                break

            payload = [_client_to_dict(c) for c in batch]
            results = adapter.score(payload)
            _apply_scores(db, batch, results)

            scored_total += len(results)
            batches += 1
            offset += BATCH_SIZE

    return {"batches": batches, "scored": scored_total}


@celery_app.task(name="app.workers.score_tasks.rescore_clients_by_ids")
def rescore_clients_by_ids(client_ids: list[int]) -> dict:
    if not client_ids:
        return {"scored": 0}

    adapter = get_scoring_adapter()
    with SessionLocal() as db:
        batch = list(db.scalars(select(Client).where(Client.id.in_(client_ids))).all())
        payload = [_client_to_dict(c) for c in batch]
        results = adapter.score(payload)
        _apply_scores(db, batch, results)

    return {"scored": len(results)}


def _client_to_dict(c: Client) -> dict:
    return {
        "id": c.id,
        "email": c.email,
        "company": c.company,
        "category": c.category,
        "tags": c.tags,
        "attributes": c.attributes,
        "is_unsubscribed": c.is_unsubscribed,
    }


def _apply_scores(db, clients, results) -> None:
    by_id = {c.id: c for c in clients}
    for res in results:
        client = by_id.get(res.client_id)
        if client is None:
            continue
        client.current_score = res.score
        db.add(
            ScoreHistory(
                client_id=client.id,
                score=res.score,
                factors=res.factors,
                algorithm_version=res.algorithm_version,
            )
        )
    db.commit()
