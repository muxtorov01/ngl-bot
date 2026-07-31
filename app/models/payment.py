from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    plan_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("plans.id"), index=True)

    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.PENDING)

    telegram_payment_charge_id: Mapped[str | None] = mapped_column(String(256), nullable=True, unique=True)
    invoice_payload: Mapped[str] = mapped_column(String(256), nullable=False)
