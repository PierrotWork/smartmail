"""Абстрактный интерфейс CRM-адаптера.

Реализуй этот протокол для конкретного CRM-сервиса вашей компании.
Всё, что специфично для конкретного CRM (аутентификация, пагинация,
маппинг полей) — инкапсулируется здесь и не утекает в бизнес-логику.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class CRMAdapter(Protocol):
    """Единый интерфейс, который обязан реализовать любой CRM-адаптер."""

    async def fetch_clients(
        self,
        updated_since: datetime | None = None,
        batch_size: int = 500,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """
        Постранично тянет клиентов из внешнего CRM.

        Возвращает итератор батчей — каждый батч это список словарей
        в нормализованном формате:

            {
                "external_id": str,           # обязательное
                "email": str,                 # обязательное
                "first_name": str | None,
                "last_name": str | None,
                "company": str | None,
                "category": str | None,
                "tags": list[str],
                "attributes": dict[str, Any], # произвольные поля из CRM
            }
        """
        ...

    async def health_check(self) -> bool:
        """Проверка доступности CRM (используется в /health)."""
        ...
