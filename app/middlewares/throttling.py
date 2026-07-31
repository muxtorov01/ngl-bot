from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from app.config import settings


class ThrottlingMiddleware(BaseMiddleware):
    """Fast in-memory rate limiter: max N messages per window-seconds per sender.
    Applied only to Message updates (anonymous sends / replies)."""

    def __init__(self) -> None:
        self._history: dict[int, deque[float]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or event.from_user is None:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.monotonic()
        window = settings.antispam_window_seconds
        limit = settings.max_messages_per_window

        history = self._history[user_id]
        while history and now - history[0] > window:
            history.popleft()

        if len(history) >= limit:
            data["rate_limited"] = True
        else:
            history.append(now)
            data["rate_limited"] = False

        return await handler(event, data)
