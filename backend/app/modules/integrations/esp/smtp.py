"""SMTP-адаптер — для локальной разработки (MailHog) и как fallback."""

from email.message import EmailMessage as MIMEMessage
from email.utils import formataddr

import aiosmtplib

from app.config import settings
from app.modules.integrations.esp.base import EmailMessage, SendResult


def _read(key: str, default: str | int | bool | None = None):
    """Читает настройку из БД с fallback на env."""
    from app.database import SessionLocal
    from app.modules.settings.service import get_value

    with SessionLocal() as db:
        v = get_value(db, key)
    return v if v not in (None, "") else default


class SMTPAdapter:
    provider_name = "smtp"

    async def send(self, message: EmailMessage) -> SendResult:
        # Оборачиваем ВСЁ в try — включая конструирование MIME. Иначе битый email
        # (например, с кириллицей до @) роняет UnicodeEncodeError и убивает всю
        # пачку рассылки. Ловим — помечаем именно эту запись как failed.
        try:
            # Заранее проверяем, что адрес корректный (ASCII local part).
            # По RFC 5321 сам email должен быть ASCII; non-ASCII допустимо
            # только в display-name (кодируется через RFC 2047).
            message.to_email.encode("ascii")
            message.from_email.encode("ascii")

            mime = MIMEMessage()
            # formataddr() правильно RFC-2047-кодирует имя (для non-ASCII вроде "Мария"),
            # а email оставляет ASCII-чистым — иначе MailHog / любой SMTP-сервер без
            # SMTPUTF8 отвечает "An address containing non-ASCII characters".
            mime["From"] = formataddr((message.from_name, message.from_email))
            mime["To"] = (
                formataddr((message.to_name, message.to_email))
                if message.to_name
                else message.to_email
            )
            mime["Subject"] = message.subject
            mime["X-Message-Id"] = message.message_id
            for k, v in message.headers.items():
                mime[k] = v

            mime.set_content(message.text_body or "")
            mime.add_alternative(message.html_body, subtype="html")
        except UnicodeEncodeError as e:
            return SendResult(
                message_id=message.message_id,
                provider_message_id=None,
                accepted=False,
                error=f"invalid email address (non-ASCII): {e}",
            )
        except Exception as e:  # noqa: BLE001
            return SendResult(
                message_id=message.message_id,
                provider_message_id=None,
                accepted=False,
                error=f"message build failed: {e}",
            )

        try:
            # Читаем актуальные SMTP-настройки из БД (с env-fallback), чтобы
            # изменения через UI применялись без перезапуска воркера.
            await aiosmtplib.send(
                mime,
                hostname=_read("smtp_host", settings.smtp_host),
                port=int(_read("smtp_port", settings.smtp_port)),
                username=_read("smtp_user") or None,
                password=_read("smtp_password") or None,
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
