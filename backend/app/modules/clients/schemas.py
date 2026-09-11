"""Pydantic-схемы клиентов."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.clients.models import ClientStatus


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    external_id: str
    email: EmailStr
    first_name: str | None
    last_name: str | None
    company: str | None
    category: str | None
    tags: list[str]
    attributes: dict[str, Any]
    current_score: float | None
    status: ClientStatus
    is_unsubscribed: bool
    synced_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ClientListResponse(BaseModel):
    items: list[ClientRead]
    total: int
    page: int
    page_size: int


class ClientFilter(BaseModel):
    """Фильтр для сегментации."""

    search: str | None = None
    category: str | None = None
    tags_any: list[str] = Field(default_factory=list)
    tags_all: list[str] = Field(default_factory=list)
    score_min: float | None = Field(default=None, ge=0, le=100)
    score_max: float | None = Field(default=None, ge=0, le=100)
    status: ClientStatus | None = None
    include_unsubscribed: bool = False
    # Произвольные атрибуты — например {"country": "RU", "is_paying": true}
    attributes_equal: dict[str, Any] = Field(default_factory=dict)


class SegmentPreview(BaseModel):
    total: int
    sample: list[ClientRead]
