"""Работа с клиентской базой: фильтрация, сегментация, апсерт."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.clients.models import Client, ClientStatus
from app.modules.clients.schemas import ClientFilter


def _apply_filter(stmt: Select, f: ClientFilter) -> Select:
    conds = []

    if f.status is not None:
        conds.append(Client.status == f.status)
    else:
        conds.append(Client.status == ClientStatus.ACTIVE)

    if not f.include_unsubscribed:
        conds.append(Client.is_unsubscribed.is_(False))

    if f.category:
        conds.append(Client.category == f.category)

    if f.score_min is not None:
        conds.append(Client.current_score >= f.score_min)
    if f.score_max is not None:
        conds.append(Client.current_score <= f.score_max)

    if f.search:
        pattern = f"%{f.search}%"
        conds.append(
            or_(
                Client.email.ilike(pattern),
                Client.first_name.ilike(pattern),
                Client.last_name.ilike(pattern),
                Client.company.ilike(pattern),
            )
        )

    # tags_any: клиент содержит любой из указанных тегов
    if f.tags_any:
        conds.append(Client.tags.op("?|")(f.tags_any))

    # tags_all: клиент содержит все указанные теги
    if f.tags_all:
        conds.append(Client.tags.op("?&")(f.tags_all))

    # attributes_equal: точное совпадение значений в JSONB
    for key, value in f.attributes_equal.items():
        conds.append(Client.attributes[key].astext == str(value))

    return stmt.where(and_(*conds))


def list_clients(
    db: Session,
    f: ClientFilter,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[Client], int]:
    base = _apply_filter(select(Client), f)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    items_stmt = (
        base.order_by(Client.current_score.desc().nullslast(), Client.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = list(db.scalars(items_stmt).all())
    return items, total


def preview_segment(db: Session, f: ClientFilter, sample_size: int = 5) -> tuple[list[Client], int]:
    """Быстрый предпросмотр сегмента для UI-конструктора."""
    base = _apply_filter(select(Client), f)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    sample = list(db.scalars(base.limit(sample_size)).all())
    return sample, total


def upsert_from_external(db: Session, records: list[dict[str, Any]]) -> tuple[int, int]:
    """
    Массовый upsert клиентов из внешнего CRM.
    Возвращает (создано, обновлено).
    Ожидаемый формат записи:
      {
        "external_id": "...", "email": "...",
        "first_name": "...", "last_name": "...", "company": "...",
        "category": "...", "tags": [...], "attributes": {...}
      }
    """
    created = 0
    updated = 0
    now = datetime.now(timezone.utc)

    for rec in records:
        ext_id = rec.get("external_id")
        email = rec.get("email")
        if not ext_id or not email:
            continue

        existing = db.scalar(select(Client).where(Client.external_id == ext_id))
        if existing is None:
            client = Client(
                external_id=ext_id,
                email=email,
                first_name=rec.get("first_name"),
                last_name=rec.get("last_name"),
                company=rec.get("company"),
                category=rec.get("category"),
                tags=rec.get("tags", []) or [],
                attributes=rec.get("attributes", {}) or {},
                synced_at=now,
            )
            db.add(client)
            created += 1
        else:
            existing.email = email
            existing.first_name = rec.get("first_name", existing.first_name)
            existing.last_name = rec.get("last_name", existing.last_name)
            existing.company = rec.get("company", existing.company)
            existing.category = rec.get("category", existing.category)
            if "tags" in rec:
                existing.tags = rec["tags"] or []
            if "attributes" in rec:
                existing.attributes = rec["attributes"] or {}
            existing.synced_at = now
            updated += 1

    db.commit()
    return created, updated
