from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message


async def safe_edit_text(message: Message, *args, **kwargs) -> None:
    """Drop-in replacement for message.edit_text().

    Telegram rejects an edit with "message is not modified" when the new
    text/markup is byte-identical to what's already shown (e.g. the user
    double-taps the same menu button). That's not a real error - there's
    nothing to fix, just nothing to send - so we swallow only that specific
    case and re-raise anything else.
    """
    try:
        await message.edit_text(*args, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
