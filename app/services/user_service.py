from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import User, UserRole
from app.repositories.link_repo import LinkRepository
from app.repositories.user_repo import UserRepository
from app.utils.i18n import detect_lang
from app.utils.tokens import generate_token


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.links = LinkRepository(session)

    async def get_or_register(
        self, telegram_id: int, username: str | None, full_name: str | None, telegram_language_code: str | None = None
    ) -> User:
        is_super_admin = telegram_id in settings.super_admin_ids
        user = await self.users.get_or_create(
            telegram_id, username, full_name, is_super_admin=is_super_admin, language=detect_lang(telegram_language_code)
        )
        if is_super_admin and not user.is_super_admin:
            user.role = UserRole.SUPER_ADMIN
            await self.session.flush()
        if not user.active_link_token:
            token = generate_token()
            await self.links.create_new_active_token(user, token)
        return user

    async def regenerate_link(self, user: User) -> str:
        token = generate_token()
        await self.links.create_new_active_token(user, token)
        return token

    async def toggle_pause(self, user: User) -> bool:
        await self.users.set_pause(user, not user.is_paused)
        return user.is_paused

    async def toggle_notifications(self, user: User) -> bool:
        await self.users.set_notifications(user, not user.notifications_enabled)
        return user.notifications_enabled

    async def set_language(self, user: User, language: str) -> None:
        await self.users.set_language(user, language)

    async def resolve_receiver_by_token(self, token: str) -> User | None:
        link = await self.links.get_active(token)
        if not link:
            return None
        return await self.users.get_by_id(link.owner_id)
