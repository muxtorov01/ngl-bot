from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Payment, Plan, User
from app.repositories.payment_repo import PaymentRepository
from app.repositories.plan_repo import PlanRepository
from app.repositories.user_repo import UserRepository


class PremiumService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plans = PlanRepository(session)
        self.payments = PaymentRepository(session)
        self.users = UserRepository(session)

    async def list_plans(self) -> list[Plan]:
        return await self.plans.list_active()

    def build_invoice_payload(self, user_id: int, plan_code: str) -> str:
        return f"premium:{plan_code}:{user_id}:{uuid.uuid4().hex[:10]}"

    async def create_pending_payment(self, user: User, plan: Plan) -> Payment:
        payload = self.build_invoice_payload(user.id, plan.code)
        return await self.payments.create_pending(user.id, plan.id, plan.stars_price, payload)

    async def finalize_successful_payment(self, invoice_payload: str, telegram_charge_id: str) -> tuple[User, Plan] | None:
        """Called from the successful_payment handler. Marks payment paid,
        extends the user's premium_until, and records a PremiumEvent for audit."""
        payment = await self.payments.get_by_payload(invoice_payload)
        if payment is None:
            return None

        plan = await self.plans.get_by_id(payment.plan_id)
        user = await self.users.get_by_id(payment.user_id)
        if plan is None or user is None:
            return None

        await self.payments.mark_paid(payment, telegram_charge_id)

        now = dt.datetime.now(dt.timezone.utc)
        expires_at = now + dt.timedelta(days=plan.duration_days)
        await self.users.activate_premium(user, expires_at)

        await self.payments.record_premium_event(
            user_id=user.id,
            plan_id=plan.id,
            payment_id=payment.id,
            activated_at=now,
            expires_at=user.premium_until or expires_at,
            duration_days=plan.duration_days,
        )
        return user, plan

    async def update_plan_price(self, plan_code: str, stars_price: int) -> Plan | None:
        plan = await self.plans.get_by_code(plan_code)
        if plan is None:
            return None
        await self.plans.update_price(plan, stars_price)
        return plan
