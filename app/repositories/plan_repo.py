from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Plan


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self) -> list[Plan]:
        result = await self.session.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.duration_days))
        return list(result.scalars().all())

    # Alias used by app/handlers/premium.py — kept so both names work.
    async def get_active_plans(self) -> list[Plan]:
        return await self.list_active()

    async def list_all(self) -> list[Plan]:
        result = await self.session.execute(select(Plan).order_by(Plan.duration_days))
        return list(result.scalars().all())

    async def get_by_code(self, code: str) -> Plan | None:
        result = await self.session.execute(select(Plan).where(Plan.code == code))
        return result.scalar_one_or_none()

    async def get_by_id(self, plan_id: int) -> Plan | None:
        return await self.session.get(Plan, plan_id)

    async def update_price(self, plan: Plan, stars_price: int) -> None:
        plan.stars_price = stars_price
        await self.session.flush()

    async def ensure_defaults(self) -> None:
        """Seed the three mandatory plans if they don't exist yet."""
        defaults = [
            ("daily", "Daily Premium", 50, 1),
            ("weekly", "Weekly Premium", 250, 7),
            ("yearly", "Yearly Premium", 4990, 365),
        ]
        for code, name, price, days in defaults:
            existing = await self.get_by_code(code)
            if not existing:
                self.session.add(Plan(code=code, name=name, stars_price=price, duration_days=days))
        await self.session.flush()
