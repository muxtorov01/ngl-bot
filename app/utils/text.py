from __future__ import annotations

from app.config import settings


def personal_link(token: str) -> str:
    return f"https://t.me/{settings.bot_username}?start={token}"


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def format_duration(seconds: int) -> str:
    minutes, secs = divmod(seconds, 60)
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"
