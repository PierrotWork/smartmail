"""Адаптер к DataNewton (https://api.datanewton.ru).

Модель работы у DataNewton — асинхронный экспорт данных через сегменты:

    1. POST /v1/segment                           создать filter_based сегмент
    2. POST /v1/segment/{id}/export               запустить экспорт (материализацию)
    3. GET  /v1/segment/{id}/export               опрашивать статус
    4. GET  /v1/segment/{id}/export/batch         скачивать данные пачками

Авторизация: query-параметр `?key=...` в каждом запросе.

Использование в приложении:
- В .env указываем DATANEWTON_API_KEY и (опционально) DATANEWTON_SEGMENT_IDS
  — через запятую перечисляем id сегментов, которые нужно синкать.
- Если DATANEWTON_SEGMENT_IDS пуст — синкаются все НЕ-reserved и НЕ-пустые
  сегменты из аккаунта.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import httpx

from app.config import settings

log = logging.getLogger(__name__)


BASE_URL = "https://api.datanewton.ru/v1"


class DataNewtonError(RuntimeError):
    """Любая ошибка, возникшая при работе с DataNewton API."""


class DataNewtonAdapter:
    """Client + high-level sync flow for DataNewton."""

    def __init__(
        self,
        api_key: str | None = None,
        segment_ids: list[int] | None = None,
        export_timeout: int = 600,
        poll_interval: int = 5,
    ) -> None:
        self.api_key = api_key or settings.datanewton_api_key
        if not self.api_key:
            raise DataNewtonError("DATANEWTON_API_KEY не задан")
        self.segment_ids = segment_ids or settings.datanewton_segment_ids_list
        self.export_timeout = export_timeout
        self.poll_interval = poll_interval
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------ context

    async def __aenter__(self) -> DataNewtonAdapter:
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _params(self, **extra: Any) -> dict[str, Any]:
        return {"key": self.api_key, **extra}

    async def _get(self, path: str, **params: Any) -> Any:
        assert self._client is not None, "Используй адаптер как async context manager"
        r = await self._client.get(f"{BASE_URL}{path}", params=self._params(**params))
        r.raise_for_status()
        return r.json()

    async def _post(self, path: str, json: dict | None = None) -> Any:
        assert self._client is not None
        r = await self._client.post(
            f"{BASE_URL}{path}", params=self._params(), json=json or {}
        )
        r.raise_for_status()
        return r.json()

    async def _delete(self, path: str) -> Any:
        assert self._client is not None
        r = await self._client.delete(f"{BASE_URL}{path}", params=self._params())
        r.raise_for_status()
        return r.json()

    # ----------------------------------------------------------- health / info

    async def health_check(self) -> bool:
        try:
            await self._get("/segment")
            return True
        except httpx.HTTPError as e:
            log.warning("DataNewton health check failed: %s", e)
            return False

    async def list_segments(self) -> list[dict[str, Any]]:
        """Список всех сегментов пользователя."""
        payload = await self._get("/segment")
        return payload.get("segments", [])

    async def get_segment(self, segment_id: int) -> dict[str, Any]:
        return await self._get(f"/segment/{segment_id}")

    # ------------------------------------------------------------ CRUD segments

    async def create_filter_segment(
        self,
        name: str,
        filter_config: dict[str, Any],
        details: str | None = None,
    ) -> int:
        """Создать filter_based сегмент, вернуть его id."""
        body: dict[str, Any] = {
            "name": name,
            # ВАЖНО: enum принимает lowercase значения
            "tag_type": "filter_based",
            "filter_config": filter_config,
        }
        if details:
            body["details"] = details
        payload = await self._post("/segment", body)
        segment_id = payload.get("id")
        if segment_id is None:
            raise DataNewtonError(f"Не удалось создать сегмент: {payload}")
        return int(segment_id)

    async def create_static_segment(
        self,
        name: str,
        ogrns_or_inns: list[str],
        details: str | None = None,
    ) -> int:
        body: dict[str, Any] = {
            "name": name,
            "tag_type": "static",
            "ogrns_or_inns": ogrns_or_inns,
        }
        if details:
            body["details"] = details
        payload = await self._post("/segment", body)
        return int(payload["id"])

    async def delete_segment(self, segment_id: int) -> None:
        await self._delete(f"/segment/{segment_id}")

    # ---------------------------------------------------------------- export

    async def start_export(self, segment_id: int) -> dict[str, Any]:
        """
        Запустить экспорт сегмента. Возвращает объект сессии, включая
        `session_id` — обязательный параметр для последующих /batch и cancel.
        """
        return await self._post(f"/segment/{segment_id}/export")

    async def get_export_status(self, segment_id: int) -> dict[str, Any]:
        return await self._get(f"/segment/{segment_id}/export")

    async def cancel_export(self, segment_id: int, session_id: int) -> None:
        """DELETE /export требует ?session_id=... — иначе 409 «Параметр отсутствует»."""
        assert self._client is not None
        r = await self._client.delete(
            f"{BASE_URL}/segment/{segment_id}/export",
            params=self._params(session_id=session_id),
        )
        r.raise_for_status()

    async def fetch_export_batch(
        self, segment_id: int, session_id: int
    ) -> dict[str, Any]:
        """
        Получить очередную пачку данных экспорта.

        ⚠️ `session_id` — обязательный query-параметр (id, полученный из
        ответа `start_export`). Без него — HTTP 409.

        DataNewton сам ведёт внутренний курсор — просто повторяй запрос,
        пока не вернётся пустая пачка.

        ⚠️ На trial-тарифе этот эндпойнт возвращает HTTP 403
        «Access denied: limit exceeded» — реальный доступ к данным
        требует платного тарифа (например, Filters API — Start).
        """
        return await self._get(
            f"/segment/{segment_id}/export/batch", session_id=session_id
        )

    async def wait_for_export(self, segment_id: int) -> dict[str, Any]:
        """Опрашивать статус, пока экспорт не завершится или не таймаутнет."""
        start = asyncio.get_event_loop().time()
        while True:
            status = await self.get_export_status(segment_id)
            # DataNewton в разных ответах использует разные ключи готовности:
            # `completed: true` или `status: "completed" | "ready"`
            if status.get("completed") or status.get("status") in {
                "ready",
                "completed",
                "COMPLETED",
            }:
                return status
            if status.get("status") in {"error", "failed", "FAILED"}:
                raise DataNewtonError(
                    f"Экспорт сегмента {segment_id} упал: {status.get('error_message')}"
                )
            if asyncio.get_event_loop().time() - start > self.export_timeout:
                raise DataNewtonError(
                    f"Экспорт сегмента {segment_id} не завершился за {self.export_timeout}с"
                )
            await asyncio.sleep(self.poll_interval)

    # -------------------------------------------------- high-level sync flow

    async def fetch_clients(
        self,
        updated_since: datetime | None = None,  # noqa: ARG002 (DN не поддерживает)
        batch_size: int = 500,  # noqa: ARG002 (DN сам решает размер батча)
    ) -> AsyncIterator[list[dict[str, Any]]]:
        """
        Полный цикл синхронизации: для каждого настроенного сегмента запускает
        экспорт, ждёт материализации и стримит данные пачками.

        `updated_since` игнорируется — у DataNewton нет инкрементального
        режима, каждый экспорт полный.
        """
        segment_ids = await self._resolve_segment_ids()
        if not segment_ids:
            log.warning("Нет сегментов для синхронизации из DataNewton")
            return

        for segment_id in segment_ids:
            log.info("DataNewton sync: segment %s — старт экспорта", segment_id)
            session = await self.start_export(segment_id)
            session_id = int(session["session_id"])
            log.info(
                "DataNewton sync: segment %s — session %s, ожидаем материализацию",
                segment_id,
                session_id,
            )

            status = await self.wait_for_export(segment_id)
            log.info(
                "DataNewton sync: segment %s — готов, всего %s записей",
                segment_id,
                status.get("total_count"),
            )

            while True:
                batch = await self.fetch_export_batch(segment_id, session_id)
                items = _extract_items(batch)
                if not items:
                    break
                yield [_normalize(item) for item in items]

    async def _resolve_segment_ids(self) -> list[int]:
        """
        Если явно указаны через DATANEWTON_SEGMENT_IDS — используем их.
        Иначе — берём все не-reserved и не-пустые сегменты пользователя.
        """
        if self.segment_ids:
            return self.segment_ids

        segments = await self.list_segments()
        return [
            int(s["id"])
            for s in segments
            if not s.get("reserved")
            and (s.get("count") or 0) > 0
        ]


# ============================================================================
# Response helpers
# ============================================================================


def _extract_items(batch_response: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Разные части DataNewton могут отдавать данные под разными ключами:
    "items" / "counterparties" / "data" / плоский список. Пробуем всё.
    """
    for key in ("items", "counterparties", "data", "results"):
        if isinstance(batch_response.get(key), list):
            return batch_response[key]
    if isinstance(batch_response, list):
        return batch_response
    return []


def _normalize(item: dict[str, Any]) -> dict[str, Any]:
    """
    Привести карточку контрагента DataNewton к внутреннему формату Client.

    DataNewton отдаёт что-то вроде:
        {
          "inn": "...",
          "ogrn": "...",
          "company": {
            "company_names": {"short_name": "...", "full_name": "..."},
            "opf": "ООО",
            "kpp": "...",
            "address": {"line_address": "...", "region_code": "77"},
            "okveds": [{"code": "62.01", "text": "..."}, ...],
            "managers": [{"first_name": "...", "last_name": "...", ...}],
            "status": {"active_status": true, ...},
            ...
          },
          "contacts": {"emails": [...], "phones": [...]} | null
        }

    Маппинг сделан «на всякий случай» — под несколько вариантов расположения
    email/phone. После первого реального экспорта имеет смысл подстроить
    точнее по итоговой структуре.
    """
    inn = item.get("inn") or ""
    ogrn = item.get("ogrn") or ""
    external_id = inn or ogrn
    if not external_id:
        # без идентификатора запись бесполезна
        return {"external_id": "", "email": "", "attributes": {"raw": item}}

    company = item.get("company") or {}
    names = company.get("company_names") or {}
    address = company.get("address") or {}
    status_block = company.get("status") or {}
    managers = company.get("managers") or []
    first_manager = managers[0] if managers else {}

    # Email/phone — возможные места
    contacts = item.get("contacts") or company.get("contacts") or {}
    emails = (
        contacts.get("emails")
        or item.get("emails")
        or company.get("emails")
        or []
    )
    phones = (
        contacts.get("phones")
        or item.get("phones")
        or company.get("phones")
        or []
    )

    # Строчный email = первый непустой
    primary_email = _first_email(emails)

    okveds = [ok.get("code") for ok in (company.get("okveds") or []) if ok.get("code")]

    return {
        "external_id": external_id,
        "email": primary_email,
        "first_name": first_manager.get("first_name") or first_manager.get("firstName"),
        "last_name": first_manager.get("last_name") or first_manager.get("lastName"),
        "company": names.get("short_name") or names.get("full_name"),
        "category": company.get("opf"),
        "tags": [],
        "attributes": {
            "inn": inn,
            "ogrn": ogrn,
            "kpp": company.get("kpp"),
            "region_code": address.get("region_code"),
            "address": address.get("line_address") or address.get("full") or "",
            "okveds": okveds,
            "emails_all": [e for e in emails if e],
            "phones_all": [p for p in phones if p],
            "manager_name": _full_name(first_manager),
            "manager_position": first_manager.get("position"),
            "registration_date": company.get("registration_date"),
            "active": status_block.get("active_status"),
            "status_text": status_block.get("status_rus_short")
            or status_block.get("status_egr"),
        },
    }


def _first_email(emails: list[Any]) -> str:
    for e in emails:
        if isinstance(e, str) and "@" in e:
            return e.strip()
        if isinstance(e, dict):
            value = e.get("value") or e.get("email")
            if value and "@" in value:
                return value.strip()
    return ""


def _full_name(manager: dict[str, Any]) -> str | None:
    parts = [
        manager.get("last_name") or manager.get("lastName"),
        manager.get("first_name") or manager.get("firstName"),
        manager.get("middle_name") or manager.get("middleName"),
    ]
    name = " ".join(p for p in parts if p)
    return name or None
