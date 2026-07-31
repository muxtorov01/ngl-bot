from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.message_repo import MessageRepository


class AntiSpamResult:
    def __init__(self, allowed: bool, reason: str | None = None) -> None:
        self.allowed = allowed
        self.reason = reason


class AntiSpamService:
    """Rate limiting + duplicate-message detection for anonymous senders.

    Rate limiting itself (max N messages per window) is enforced in-memory by
    ThrottlingMiddleware for speed; this service adds the DB-backed duplicate
    message check which needs message history.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.messages = MessageRepository(session)

    async def check_duplicate(self, sender_telegram_id: int, receiver_id: int, text_content: str | None) -> AntiSpamResult:
        if not text_content:
            return AntiSpamResult(True)
        window_start = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=10)
        count = await self.messages.recent_identical_count(sender_telegram_id, receiver_id, text_content, window_start)
        if count >= 1:
            return AntiSpamResult(False, "duplicate_message")
        return AntiSpamResult(True)
