from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Broadcast, BroadcastStatus, User
from app.repositories.moderation_repo import BroadcastRepository

logger = logging.getLogger(__name__)

_SEND_CONCURRENCY = 20
_SEND_DELAY_SECONDS = 0.05  # stay well under Telegram's global rate limits


class BroadcastService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.broadcasts = BroadcastRepository(session)

    async def _all_recipient_ids(self) -> list[int]:
        result = await self.session.execute(select(User.telegram_id).where(User.is_banned.is_(False)))
        return [row[0] for row in result.all()]

    async def create_and_run(
        self, bot: Bot, created_by: int, text_content: str | None, photo_file_id: str | None
    ) -> Broadcast:
        recipient_ids = await self._all_recipient_ids()
        broadcast = await self.broadcasts.create(created_by, text_content, photo_file_id, len(recipient_ids))
        broadcast.status = BroadcastStatus.RUNNING
        await self.session.flush()
        await self.session.commit()

        semaphore = asyncio.Semaphore(_SEND_CONCURRENCY)

        async def send_one(chat_id: int) -> None:
            async with semaphore:
                try:
                    if photo_file_id:
                        await bot.send_photo(chat_id, photo_file_id, caption=text_content)
                    else:
                        await bot.send_message(chat_id, text_content or "")
                    await self.broadcasts.log_result(broadcast, chat_id, True, None)
                except TelegramAPIError as exc:
                    logger.warning("Broadcast failed for %s: %s", chat_id, exc)
                    await self.broadcasts.log_result(broadcast, chat_id, False, str(exc))
                await asyncio.sleep(_SEND_DELAY_SECONDS)

        await asyncio.gather(*(send_one(cid) for cid in recipient_ids))

        broadcast.status = BroadcastStatus.DONE
        await self.session.flush()
        return broadcast
