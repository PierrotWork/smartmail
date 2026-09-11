"""HTTP-эндпойнты клиентской базы."""

from fastapi import APIRouter, HTTPException, Query, status

from app.deps import CurrentUser, DbSession
from app.modules.clients import service
from app.modules.clients.models import Client
from app.modules.clients.schemas import (
    ClientFilter,
    ClientListResponse,
    ClientRead,
    SegmentPreview,
)

router = APIRouter()


@router.post("/search", response_model=ClientListResponse)
def search_clients(
    filter_: ClientFilter,
    db: DbSession,
    user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> ClientListResponse:
    items, total = service.list_clients(db, filter_, page=page, page_size=page_size)
    return ClientListResponse(
        items=[ClientRead.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/segment-preview", response_model=SegmentPreview)
def segment_preview(
    filter_: ClientFilter,
    db: DbSession,
    user: CurrentUser,
) -> SegmentPreview:
    """Быстрый предпросмотр: сколько клиентов попадёт в сегмент и первые 5 из них."""
    sample, total = service.preview_segment(db, filter_)
    return SegmentPreview(
        total=total,
        sample=[ClientRead.model_validate(c) for c in sample],
    )


@router.get("/{client_id}", response_model=ClientRead)
def get_client(client_id: int, db: DbSession, user: CurrentUser) -> ClientRead:
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Клиент не найден")
    return ClientRead.model_validate(client)


@router.post("/sync", status_code=202)
def trigger_sync(user: CurrentUser) -> dict:
    """Ручной запуск синхронизации с внешним CRM."""
    from app.workers.sync_tasks import sync_all_clients

    task = sync_all_clients.delay()
    return {"task_id": task.id, "status": "queued"}
