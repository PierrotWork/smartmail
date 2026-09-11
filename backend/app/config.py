"""Настройки приложения — читаются из переменных окружения / .env."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === App ===
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = "change-me"
    app_debug: bool = True

    # === Database ===
    database_url: str

    # === Redis / Celery ===
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # === JWT ===
    jwt_algorithm: str = "HS256"
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7

    # === CORS ===
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # === CRM ===
    crm_api_base_url: str = ""
    crm_api_key: str = ""
    crm_sync_interval_minutes: int = 30

    # === ESP ===
    esp_provider: Literal["smtp", "unisender", "sendgrid", "mailgun"] = "smtp"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = False
    smtp_from_name: str = "SmartMail"
    smtp_from_email: str = "noreply@example.com"
    unisender_api_key: str = ""
    sendgrid_api_key: str = ""

    # === Scoring ===
    scoring_provider: Literal["mock", "http"] = "mock"
    scoring_http_url: str = ""
    scoring_http_timeout: int = 5


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
