from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, PaymentStatus, PremiumEvent


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_pending(self, user_id: int, plan_id: int, stars_amount: int, invoice_payload: str) -> Payment:
        payment = Payment(
            user_id=user_id,
            plan_id=plan_id,
            stars_amount=stars_amount,
            status=PaymentStatus.PENDING,
            invoice_payload=invoice_payload,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_payload(self, invoice_payload: str) -> Payment | None:
        result = await self.session.execute(select(Payment).where(Payment.invoice_payload == invoice_payload))
        return result.scalar_one_or_none()

    async def mark_paid(self, payment: Payment, charge_id: str) -> None:
        payment.status = PaymentStatus.PAID
        payment.telegram_payment_charge_id = charge_id
        await self.session.flush()

    async def total_revenue_stars(self) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.sum(Payment.stars_amount), 0)).where(Payment.status == PaymentStatus.PAID)
        )
        return int(result.scalar_one())

    async def record_premium_event(
        self, user_id: int, plan_id: int, payment_id: int | None, activated_at: dt.datetime, expires_at: dt.datetime, duration_days: int
    ) -> PremiumEvent:
        event = PremiumEvent(
            user_id=user_id,
            payment_id=payment_id,
            plan_id=plan_id,
            activated_at=activated_at,
            expires_at=expires_at,
            duration_days=duration_days,
        )
        self.session.add(event)
        await self.session.flush()
        return event
