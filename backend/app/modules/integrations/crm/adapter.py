"""Конкретная реализация CRM-адаптера.

TODO: замени on-request/эндпойнты/маппинг полей на реальные —
согласно документации вашего CRM-сервиса.
"""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx

from app.config import settings


class GenericCRMAdapter:
    """
    Заготовка адаптера — работает с типовым REST API, использующим
    Bearer-токен и курсорную пагинацию. Правь под вашу CRM.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.crm_api_base_url).rstrip("/")
        self.api_key = api_key or settings.crm_api_key
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GenericCRMAdapter":
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> bool:
        if self._client is None:
            return False
        try:
            r = await self._client.get("/ping")
            return r.status_code == 200
        except httpx.HTTPError:
            return False

    async def fetch_clients(
        self,
        updated_since: datetime | None = None,
        batch_size: int = 500,
    ) -> AsyncIterator[list[dict[str, Any]]]:
        assert self._client is not None, "Используйте адаптер как async context manager"

        cursor: str | None = None
        params: dict[str, Any] = {"limit": batch_size}
        if updated_since is not None:
            params["updated_since"] = updated_since.isoformat()

        while True:
            if cursor:
                params["cursor"] = cursor

            r = await self._client.get("/clients", params=params)
            r.raise_for_status()
            payload = r.json()

            raw_items: list[dict[str, Any]] = payload.get("items", [])
            batch = [self._normalize(item) for item in raw_items]
            if batch:
                yield batch

            cursor = payload.get("next_cursor")
            if not cursor or not raw_items:
                break

    @staticmethod
    def _normalize(item: dict[str, Any]) -> dict[str, Any]:
        """
        Приведение CRM-специфичной записи к внутреннему формату приложения.
        Правь маппинг под вашу CRM.
        """
        return {
            "external_id": str(item["id"]),
            "email": item["email"],
            "first_name": item.get("first_name"),
            "last_name": item.get("last_name"),
            "company": item.get("company"),
            "category": item.get("category") or item.get("type"),
            "tags": item.get("tags", []),
            "attributes": {
                k: v
                for k, v in item.items()
                if k
                not in {
                    "id",
                    "email",
                    "first_name",
                    "last_name",
                    "company",
                    "category",
                    "type",
                    "tags",
                }
            },
        }


def get_crm_adapter() -> GenericCRMAdapter:
    """Фабрика — тут можно возвращать разные адаптеры по env."""
    return GenericCRMAdapter()
