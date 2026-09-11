"""Задачи отправки писем."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select

from app.database import SessionLocal
from app.modules.campaigns.models import (
    Campaign,
    CampaignRecipient,
    CampaignStatus,
    RecipientStatus,
)
from app.modules.clients.models import Client
from app.modules.integrations.esp.base import EmailMessage
from app.modules.integrations.esp.smtp import get_esp_adapter
from app.modules.templates import service as tmpl_service
from app.modules.templates.models import EmailTemplate
from app.workers.celery_app import celery_app

log = logging.getLogger(__name__)

BATCH_SIZE = 100


@celery_app.task(name="app.workers.send_tasks.send_campaign", bind=True)
def send_campaign(self, campaign_id: int) -> dict:
    """Отправка рассылки батчами."""
    try:
        return asyncio.run(_send(campaign_id))
    except Exception:  # noqa: BLE001
        log.exception("send_campaign failed for %s", campaign_id)
        with SessionLocal() as db:
            campaign = db.get(Campaign, campaign_id)
            if campaign:
                campaign.status = CampaignStatus.FAILED
                db.commit()
        raise


async def _send(campaign_id: int) -> dict:
    esp = get_esp_adapter()
    sent_ok = 0
    sent_failed = 0

    with SessionLocal() as db:
        campaign = db.get(Campaign, campaign_id)
        if campaign is None or campaign.status != CampaignStatus.SENDING:
            return {"skipped": True, "reason": "not in SENDING status"}

        template = db.get(EmailTemplate, campaign.template_id)
        if template is None:
            campaign.status = CampaignStatus.FAILED
            db.commit()
            return {"error": "template not found"}

        while True:
            recipients = list(
                db.scalars(
                    select(CampaignRecipient)
                    .where(
                        CampaignRecipient.campaign_id == campaign.id,
                        CampaignRecipient.status == RecipientStatus.PENDING,
                    )
                    .limit(BATCH_SIZE)
                ).all()
            )
            if not recipients:
                break

            client_ids = [r.client_id for r in recipients]
            clients = {
                c.id: c
                for c in db.scalars(select(Client).where(Client.id.in_(client_ids))).all()
            }

            messages: list[EmailMessage] = []
            recipient_by_msg_id: dict[str, CampaignRecipient] = {}

            for r in recipients:
                client = clients.get(r.client_id)
                if client is None or client.is_unsubscribed:
                    r.status = RecipientStatus.UNSUBSCRIBED
                    continue

                try:
                    variables = _build_variables(client)
                    subject, html, text = tmpl_service.render_subject_and_body(
                        template, variables
                    )
                except Exception as e:  # noqa: BLE001
                    log.warning("Template render failed for client %s: %s", client.id, e)
                    r.status = RecipientStatus.FAILED
                    r.bounced_reason = f"render: {e}"
                    continue

                msg = EmailMessage(
                    to_email=client.email,
                    to_name=_full_name(client),
                    subject=subject,
                    html_body=html,
                    text_body=text,
                    from_name=campaign.sender_name,
                    from_email=campaign.sender_email,
                    message_id=r.message_id,
                    headers={
                        "X-Campaign-Id": str(campaign.id),
                        "List-Unsubscribe": f"<mailto:unsubscribe@{campaign.sender_email.split('@')[-1]}>",
                    },
                )
                messages.append(msg)
                recipient_by_msg_id[r.message_id] = r

            results = await esp.send_batch(messages) if messages else []
            now = datetime.now(UTC)
            for res in results:
                r = recipient_by_msg_id.get(res.message_id)
                if r is None:
                    continue
                if res.accepted:
                    r.status = RecipientStatus.SENT
                    r.sent_at = now
                    sent_ok += 1
                else:
                    r.status = RecipientStatus.FAILED
                    r.bounced_reason = res.error
                    sent_failed += 1

            db.commit()

        # Все получатели обработаны — завершаем рассылку
        campaign.status = CampaignStatus.COMPLETED
        campaign.finished_at = datetime.now(UTC)
        db.commit()

    return {"campaign_id": campaign_id, "sent": sent_ok, "failed": sent_failed}


def _full_name(c: Client) -> str | None:
    parts = [c.first_name, c.last_name]
    name = " ".join(p for p in parts if p)
    return name or None


def _build_variables(c: Client) -> dict:
    """Подготовить переменные для шаблона — стандартные + атрибуты клиента."""
    return {
        "email": c.email,
        "name": _full_name(c) or c.email,
        "first_name": c.first_name or "",
        "last_name": c.last_name or "",
        "company": c.company or "",
        "category": c.category or "",
        **c.attributes,
    }
