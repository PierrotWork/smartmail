"""Сервис работы с настройками.

Каждая настройка описана в реестре KNOWN_SETTINGS с метаданными:
  section  — раздел UI (api_keys / email / olm)
  label    — как называть в UI
  kind     — тип поля (string / password / number / select)
  choices  — для select-полей
  secret   — маскировать ли в API-ответе
  env      — имя env-переменной для fallback (при отсутствии в БД)

При чтении значения: сначала БД, потом env через settings.<env>.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings as env_settings
from app.modules.settings.models import AppSetting

# ---------------------------------------------------------------- registry

KNOWN_SETTINGS: dict[str, dict[str, Any]] = {
    # === API keys ===
    "crm_provider": {
        "section": "api_keys",
        "label": "CRM провайдер",
        "kind": "select",
        "choices": ["datanewton", "generic"],
        "secret": False,
        "env": "crm_provider",
    },
    "datanewton_api_key": {
        "section": "api_keys",
        "label": "DataNewton API-ключ",
        "kind": "password",
        "secret": True,
        "env": "datanewton_api_key",
        "help": "https://datanewton.ru → Личный кабинет → API-ключи",
    },
    "datanewton_segment_ids": {
        "section": "api_keys",
        "label": "ID сегментов DataNewton (через запятую, пусто = все)",
        "kind": "string",
        "secret": False,
        "env": "datanewton_segment_ids",
    },

    # === Email sender ===
    "esp_provider": {
        "section": "email",
        "label": "Провайдер отправки писем",
        "kind": "select",
        "choices": ["smtp", "unisender", "sendgrid", "mailgun"],
        "secret": False,
        "env": "esp_provider",
    },
    "smtp_host": {
        "section": "email",
        "label": "SMTP host",
        "kind": "string",
        "secret": False,
        "env": "smtp_host",
    },
    "smtp_port": {
        "section": "email",
        "label": "SMTP port",
        "kind": "number",
        "secret": False,
        "env": "smtp_port",
    },
    "smtp_user": {
        "section": "email",
        "label": "SMTP логин",
        "kind": "string",
        "secret": False,
        "env": "smtp_user",
    },
    "smtp_password": {
        "section": "email",
        "label": "SMTP пароль",
        "kind": "password",
        "secret": True,
        "env": "smtp_password",
    },
    "smtp_from_name": {
        "section": "email",
        "label": "Имя отправителя по умолчанию",
        "kind": "string",
        "secret": False,
        "env": "smtp_from_name",
    },
    "smtp_from_email": {
        "section": "email",
        "label": "Email отправителя по умолчанию",
        "kind": "string",
        "secret": False,
        "env": "smtp_from_email",
    },
    "unisender_api_key": {
        "section": "email",
        "label": "Unisender API-ключ",
        "kind": "password",
        "secret": True,
        "env": "unisender_api_key",
    },
    "sendgrid_api_key": {
        "section": "email",
        "label": "SendGrid API-ключ",
        "kind": "password",
        "secret": True,
        "env": "sendgrid_api_key",
    },

    # === OLM keys (уточнить назначение) ===
    "olm_api_key": {
        "section": "olm",
        "label": "OLM API-ключ",
        "kind": "password",
        "secret": True,
        "env": None,
    },
    "olm_api_url": {
        "section": "olm",
        "label": "OLM API URL",
        "kind": "string",
        "secret": False,
        "env": None,
    },
    "olm_model": {
        "section": "olm",
        "label": "OLM модель / профиль",
        "kind": "string",
        "secret": False,
        "env": None,
    },
}


SECTION_TITLES = {
    "api_keys": "API-ключи",
    "email": "Отправитель писем",
    "olm": "OLM keys",
}


# ---------------------------------------------------------------- helpers


def _mask(value: str | None) -> str | None:
    """Замаскировать секрет: первые 3 + звёзды + последние 3."""
    if value is None or value == "":
        return None
    if len(value) <= 8:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def get_value(db: Session, key: str) -> str | None:
    """Прочитать значение: БД → env fallback."""
    row = db.get(AppSetting, key)
    if row is not None and row.value not in (None, ""):
        return row.value
    meta = KNOWN_SETTINGS.get(key, {})
    env_field = meta.get("env")
    if env_field:
        value = getattr(env_settings, env_field, None)
        if value not in (None, ""):
            return str(value)
    return None


def set_value(db: Session, key: str, value: str | None) -> None:
    """Записать значение в БД (upsert)."""
    row = db.get(AppSetting, key)
    if row is None:
        db.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    db.commit()


def delete_value(db: Session, key: str) -> None:
    """Удалить override — вернёмся к env-fallback."""
    row = db.get(AppSetting, key)
    if row is not None:
        db.delete(row)
        db.commit()


def list_all(db: Session) -> list[dict[str, Any]]:
    """
    Вернуть все известные настройки с метаданными и текущими значениями.
    Секреты маскируются.
    """
    db_values = {
        s.key: s.value for s in db.scalars(select(AppSetting)).all()
    }

    result = []
    for key, meta in KNOWN_SETTINGS.items():
        db_val = db_values.get(key)
        env_val = None
        if meta.get("env"):
            env_val = getattr(env_settings, meta["env"], None)
            if env_val is not None:
                env_val = str(env_val)

        # Эффективное значение (что реально используется)
        effective = db_val if (db_val not in (None, "")) else env_val

        # Маскирование
        display = _mask(effective) if meta.get("secret") else effective

        result.append({
            "key": key,
            "section": meta["section"],
            "section_title": SECTION_TITLES.get(meta["section"], meta["section"]),
            "label": meta["label"],
            "kind": meta.get("kind", "string"),
            "choices": meta.get("choices"),
            "secret": meta.get("secret", False),
            "help": meta.get("help"),
            "value": display,
            "is_overridden": db_val not in (None, ""),
            "has_env_default": env_val not in (None, ""),
        })
    return result
