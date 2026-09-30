"""Модель хранения настроек приложения в БД.

Настройки-ключи хранятся как обычные строки. Простой key-value.
Для секретов используется маскирование при чтении через API — само значение
хранится как есть (для MVP; TODO: добавить шифрование Fernet при передаче
в прод).
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
