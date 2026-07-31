from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.db import get_session


class DbSessionMiddleware(BaseMiddleware):
    """Opens one AsyncSession per update and injects it as `session` into handler data.
    Commits on success, rolls back on exception (handled by get_session context manager)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with get_session() as session:
            data["session"] = session
            return await handler(event, data)
