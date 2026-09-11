"""Модели клиентов и истории скоров."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ClientStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)

    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    attributes: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    current_score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    status: Mapped[ClientStatus] = mapped_column(
        String(16), default=ClientStatus.ACTIVE, nullable=False, index=True
    )
    is_unsubscribed: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)

    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    score_history: Mapped[list["ScoreHistory"]] = relationship(
        back_populates="client", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_clients_status_score", "status", "current_score"),)


class ScoreHistory(Base):
    __tablename__ = "score_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    factors: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False)

    client: Mapped[Client] = relationship(back_populates="score_history")
