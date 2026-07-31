from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PremiumEvent(TimestampMixin, Base):
    """Audit log of every premium activation/extension, used as the boundary
    for can_reveal_sender: only messages received after activated_at may be revealed."""

    __tablename__ = "premium_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    payment_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("payments.id"), nullable=True)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("plans.id"), nullable=False)

    activated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
