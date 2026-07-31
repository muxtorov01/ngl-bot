from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import LinkToken, User


class LinkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_new_active_token(self, owner: User, token: str) -> LinkToken:
        """Deactivate any existing tokens for this owner, then create + activate a new one."""
        await self.session.execute(
            update(LinkToken).where(LinkToken.owner_id == owner.id).values(is_active=False)
        )
        link = LinkToken(owner_id=owner.id, token=token, is_active=True)
        self.session.add(link)
        owner.active_link_token = token
        await self.session.flush()
        return link

    async def get_active(self, token: str) -> LinkToken | None:
        result = await self.session.execute(
            select(LinkToken).where(LinkToken.token == token, LinkToken.is_active.is_(True))
        )
        return result.scalar_one_or_none()
