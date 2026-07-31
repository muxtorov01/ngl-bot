from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole
from app.repositories.moderation_repo import ReportRepository
from app.repositories.payment_repo import PaymentRepository
from app.repositories.user_repo import UserRepository


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.payments = PaymentRepository(session)
        self.reports = ReportRepository(session)

    async def overview(self) -> dict:
        since = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=7)
        return {
            "total_users": await self.users.count_total(),
            "active_users_7d": await self.users.count_active_since(since),
            "premium_users": await self.users.count_premium(),
            "revenue_stars": await self.payments.total_revenue_stars(),
        }

    async def ban_user(self, user: User) -> None:
        await self.users.set_ban(user, True)

    async def unban_user(self, user: User) -> None:
        await self.users.set_ban(user, False)

    async def open_reports(self, limit: int = 20):
        return await self.reports.list_open(limit)

    # ---- Admin management (super admin only, enforced by the caller) ----

    async def list_admins(self) -> list[User]:
        return await self.users.list_admins()

    async def promote_to_admin(self, user: User) -> None:
        await self.users.set_role(user, UserRole.ADMIN)

    async def demote_admin(self, user: User) -> None:
        await self.users.set_role(user, UserRole.USER)
