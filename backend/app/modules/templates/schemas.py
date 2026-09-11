"""Схемы шаблонов."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subject: str = Field(min_length=1, max_length=500)
    html_body: str
    text_body: str | None = None
    variables: list[str] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    html_body: str | None = None
    text_body: str | None = None
    variables: list[str] | None = None


class TemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    subject: str
    html_body: str
    text_body: str | None
    variables: list[str]
    version: int
    created_at: datetime
    updated_at: datetime


class PreviewRequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)
