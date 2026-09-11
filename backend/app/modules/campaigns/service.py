"""Бизнес-логика рассылок."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.campaigns.models import (
    Campaign,
    CampaignRecipient,
    CampaignStatus,
    RecipientStatus,
)
from app.modules.campaigns.schemas import CampaignCreate, CampaignStats
from app.modules.clients import service as clients_service
from app.modules.clients.schemas import ClientFilter
from app.modules.templates.models import EmailTemplate


class CampaignError(Exception):
    pass


def create_campaign(db: Session, payload: CampaignCreate, created_by_id: int | None) -> Campaign:
    if db.get(EmailTemplate, payload.template_id) is None:
        raise CampaignError("Шаблон не найден")

    campaign = Campaign(
        name=payload.name,
        description=payload.description,
        template_id=payload.template_id,
        segment_filter=payload.segment_filter.model_dump(),
        sender_name=payload.sender_name,
        sender_email=payload.sender_email,
        scheduled_at=payload.scheduled_at,
        throttle_per_hour=payload.throttle_per_hour,
        status=CampaignStatus.DRAFT,
        created_by_id=created_by_id,
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


def freeze_segment(db: Session, campaign: Campaign) -> int:
    """
    Материализовать сегмент — сделать снимок текущих получателей
    и создать записи CampaignRecipient. Вызывается при запуске рассылки.
    """
    if campaign.status != CampaignStatus.DRAFT:
        raise CampaignError("Сегмент можно материализовать только для черновика")

    filter_ = ClientFilter.model_validate(campaign.segment_filter)
    clients, total = clients_service.list_clients(db, filter_, page=1, page_size=1_000_000)

    for client in clients:
        recipient = CampaignRecipient(
            campaign_id=campaign.id,
            client_id=client.id,
            message_id=uuid.uuid4().hex,
            status=RecipientStatus.PENDING,
        )
        db.add(recipient)

    db.commit()
    return total


def start_campaign(db: Session, campaign_id: int) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise CampaignError("Рассылка не найдена")
    if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
        raise CampaignError(f"Нельзя запустить рассылку в статусе '{campaign.status}'")

    if not campaign.recipients:
        freeze_segment(db, campaign)

    campaign.status = CampaignStatus.SENDING
    campaign.started_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(campaign)

    # Постановка задачи в очередь отправки
    from app.workers.send_tasks import send_campaign

    send_campaign.delay(campaign.id)
    return campaign


def cancel_campaign(db: Session, campaign_id: int) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        raise CampaignError("Рассылка не найдена")
    if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
        raise CampaignError("Отменить можно только черновик или запланированную рассылку")

    campaign.status = CampaignStatus.CANCELLED
    db.commit()
    db.refresh(campaign)
    return campaign


def get_stats(db: Session, campaign_id: int) -> CampaignStats:
    stmt = (
        select(CampaignRecipient.status, func.count(CampaignRecipient.id))
        .where(CampaignRecipient.campaign_id == campaign_id)
        .group_by(CampaignRecipient.status)
    )
    rows = db.execute(stmt).all()
    counts = {status.value: 0 for status in RecipientStatus}
    total = 0
    for status, cnt in rows:
        counts[status.value if hasattr(status, "value") else status] = cnt
        total += cnt

    return CampaignStats(
        total=total,
        pending=counts["pending"],
        sent=counts["sent"],
        delivered=counts["delivered"],
        opened=counts["opened"],
        clicked=counts["clicked"],
        bounced=counts["bounced"],
        failed=counts["failed"],
        unsubscribed=counts["unsubscribed"],
    )
