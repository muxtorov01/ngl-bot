from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Plan(TimestampMixin, Base):
    """Admin-configurable premium subscription plan, priced in Telegram Stars (XTR)."""

    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)  # e.g. "daily"
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    stars_price: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
