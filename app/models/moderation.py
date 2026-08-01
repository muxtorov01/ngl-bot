from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Block(TimestampMixin, Base):
    """A receiver blocking a specific anonymous sender (premium feature)."""

    __tablename__ = "blocks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    blocked_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)

    __table_args__ = ()


class ReportStatus(str, enum.Enum):
    OPEN = "open"
    REVIEWED = "reviewed"
    DISMISSED = "dismissed"


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("messages.id", ondelete="CASCADE"), index=True)
    reporter_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus, name="report_status", values_callable=lambda x: [e.value for e in x]), default=ReportStatus.OPEN)


class BroadcastStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class Broadcast(TimestampMixin, Base):
    __tablename__ = "broadcasts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[BroadcastStatus] = mapped_column(Enum(BroadcastStatus, name="broadcast_status", values_callable=lambda x: [e.value for e in x]), default=BroadcastStatus.PENDING)
    total_targets: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)


class BroadcastLog(TimestampMixin, Base):
    __tablename__ = "broadcast_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    broadcast_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("broadcasts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class Setting(TimestampMixin, Base):
    """Generic key-value store for admin-tunable settings (e.g. captcha_enabled)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
