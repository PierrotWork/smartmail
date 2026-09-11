"""Абстрактный интерфейс отправки писем."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass
class EmailMessage:
    to_email: str
    to_name: str | None
    subject: str
    html_body: str
    text_body: str | None
    from_name: str
    from_email: str
    # Уникальный ID сообщения — прокидывается в вебхуки для сопоставления с CampaignRecipient
    message_id: str
    # Заголовки (X-Campaign-Id, List-Unsubscribe и т. д.)
    headers: dict[str, str]


@dataclass
class SendResult:
    message_id: str
    provider_message_id: str | None
    accepted: bool
    error: str | None = None


@runtime_checkable
class ESPAdapter(Protocol):
    """Единый интерфейс поверх конкретного провайдера отправки."""

    provider_name: str

    async def send(self, message: EmailMessage) -> SendResult: ...

    async def send_batch(self, messages: list[EmailMessage]) -> list[SendResult]: ...
