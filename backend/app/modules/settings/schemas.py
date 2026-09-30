"""Схемы для API настроек."""

from typing import Any

from pydantic import BaseModel


class SettingItem(BaseModel):
    key: str
    section: str
    section_title: str
    label: str
    kind: str  # "string" | "password" | "number" | "select"
    choices: list[str] | None = None
    secret: bool = False
    help: str | None = None
    value: str | None = None  # маскировано для secret
    is_overridden: bool = False  # переопределено в UI
    has_env_default: bool = False  # есть значение из .env


class SettingUpdate(BaseModel):
    value: str | None  # None или "" — удалить override (вернуться к env)
