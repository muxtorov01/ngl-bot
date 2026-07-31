from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserRole


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
        is_super_admin: bool = False,
        language: str = "en",
    ) -> User:
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            changed = False
            if user.username != username:
                user.username = username
                changed = True
            if user.full_name != full_name:
                user.full_name = full_name
                changed = True
            if changed:
                await self.session.flush()
            return user

        user = User(
            id=telegram_id,
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            role=UserRole.SUPER_ADMIN if is_super_admin else UserRole.USER,
            language=language,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def set_link_token(self, user: User, token: str) -> None:
        user.active_link_token = token
        await self.session.flush()

    async def get_by_link_token(self, token: str) -> User | None:
        result = await self.session.execute(select(User).where(User.active_link_token == token))
        return result.scalar_one_or_none()

    async def set_ban(self, user: User, banned: bool) -> None:
        user.is_banned = banned
        await self.session.flush()

    async def set_pause(self, user: User, paused: bool) -> None:
        user.is_paused = paused
        await self.session.flush()

    async def set_notifications(self, user: User, enabled: bool) -> None:
        user.notifications_enabled = enabled
        await self.session.flush()

    async def set_language(self, user: User, language: str) -> None:
        user.language = language
        await self.session.flush()

    async def set_role(self, user: User, role: UserRole) -> None:
        user.role = role
        await self.session.flush()

    async def list_admins(self) -> list[User]:
        result = await self.session.execute(select(User).where(User.role == UserRole.ADMIN))
        return list(result.scalars().all())

    async def activate_premium(self, user: User, until: dt.datetime) -> None:
        # Extend from the later of "now" or existing expiry, so stacking purchases works.
        now = dt.datetime.now(dt.timezone.utc)
        base = user.premium_until if (user.premium_until and user.premium_until > now) else now
        user.premium_until = max(until, base)
        await self.session.flush()

    async def count_total(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def count_active_since(self, since: dt.datetime) -> int:
        result = await self.session.execute(select(func.count(User.id)).where(User.updated_at >= since))
        return result.scalar_one()

    async def count_premium(self) -> int:
        now = dt.datetime.now(dt.timezone.utc)
        result = await self.session.execute(select(func.count(User.id)).where(User.premium_until > now))
        return result.scalar_one()
