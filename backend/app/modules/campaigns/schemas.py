"""Схемы рассылок."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.campaigns.models import CampaignStatus
from app.modules.clients.schemas import ClientFilter


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    template_id: int
    segment_filter: ClientFilter
    sender_name: str
    sender_email: EmailStr
    scheduled_at: datetime | None = None
    throttle_per_hour: int = Field(default=0, ge=0, le=100000)


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    template_id: int | None = None
    segment_filter: ClientFilter | None = None
    sender_name: str | None = None
    sender_email: EmailStr | None = None
    scheduled_at: datetime | None = None
    throttle_per_hour: int | None = Field(default=None, ge=0, le=100000)


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    template_id: int
    segment_filter: dict
    sender_name: str
    sender_email: EmailStr
    status: CampaignStatus
    scheduled_at: datetime | None
    started_at: datetime | None
    finished_at: datetime | None
    throttle_per_hour: int
    created_at: datetime
    updated_at: datetime


class CampaignStats(BaseModel):
    total: int
    pending: int
    sent: int
    delivered: int
    opened: int
    clicked: int
    bounced: int
    failed: int
    unsubscribed: int

    @property
    def open_rate(self) -> float:
        return round(self.opened / self.delivered * 100, 2) if self.delivered else 0.0

    @property
    def click_rate(self) -> float:
        return round(self.clicked / self.delivered * 100, 2) if self.delivered else 0.0
