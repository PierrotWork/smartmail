"""SMTP-адаптер — для локальной разработки (MailHog) и как fallback."""

from email.message import EmailMessage as MIMEMessage

import aiosmtplib

from app.config import settings
from app.modules.integrations.esp.base import EmailMessage, SendResult


class SMTPAdapter:
    provider_name = "smtp"

    async def send(self, message: EmailMessage) -> SendResult:
        mime = MIMEMessage()
        mime["From"] = f"{message.from_name} <{message.from_email}>"
        mime["To"] = (
            f"{message.to_name} <{message.to_email}>" if message.to_name else message.to_email
        )
        mime["Subject"] = message.subject
        mime["X-Message-Id"] = message.message_id
        for k, v in message.headers.items():
            mime[k] = v

        mime.set_content(message.text_body or "")
        mime.add_alternative(message.html_body, subtype="html")

        try:
            await aiosmtplib.send(
                mime,
                hostname=settings.smtp_host,
                port=settings.smtp_port,
                username=settings.smtp_user or None,
                password=settings.smtp_password or None,
                use_tls=settings.smtp_use_tls,
                timeout=30,
            )
            return SendResult(
                message_id=message.message_id,
                provider_message_id=None,
                accepted=True,
            )
        except Exception as e:  # noqa: BLE001
            return SendResult(
                message_id=message.message_id,
                provider_message_id=None,
                accepted=False,
                error=str(e),
            )

    async def send_batch(self, messages: list[EmailMessage]) -> list[SendResult]:
        # SMTP не поддерживает батч-API — просто последовательная отправка.
        return [await self.send(m) for m in messages]


def get_esp_adapter():
    provider = settings.esp_provider
    if provider == "smtp":
        return SMTPAdapter()
    # TODO: реализовать UnisenderAdapter, SendGridAdapter, MailgunAdapter
    raise NotImplementedError(f"ESP provider '{provider}' пока не реализован")
