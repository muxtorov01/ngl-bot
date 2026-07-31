"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def _get_int_list(name: str) -> list[int]:
    raw = os.getenv(name, "")
    result: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() or (part.startswith("-") and part[1:].isdigit()):
            result.append(int(part))
    return result


@dataclass(frozen=True)
class Settings:
    bot_token: str = field(default_factory=lambda: _get_env("BOT_TOKEN", required=True))
    bot_username: str = field(default_factory=lambda: _get_env("BOT_USERNAME", required=True))

    database_url: str = field(default_factory=lambda: _get_env("DATABASE_URL", required=True))

    webhook_base_url: str = field(default_factory=lambda: _get_env("WEBHOOK_BASE_URL", required=True))
    webhook_path: str = field(default_factory=lambda: _get_env("WEBHOOK_PATH", "/webhook"))
    webhook_secret: str = field(default_factory=lambda: _get_env("WEBHOOK_SECRET", required=True))

    web_server_host: str = field(default_factory=lambda: _get_env("WEB_SERVER_HOST", "0.0.0.0"))
    web_server_port: int = field(default_factory=lambda: int(_get_env("PORT", "8080")))

    super_admin_ids: list[int] = field(default_factory=lambda: _get_int_list("SUPER_ADMIN_IDS"))

    # Anti-spam
    max_messages_per_window: int = field(default_factory=lambda: int(_get_env("MAX_MSG_PER_WINDOW", "3")))
    antispam_window_seconds: int = field(default_factory=lambda: int(_get_env("ANTISPAM_WINDOW_SECONDS", "30")))

    # Media limits
    max_voice_seconds: int = field(default_factory=lambda: int(_get_env("MAX_VOICE_SECONDS", "60")))
    max_voice_bytes: int = field(default_factory=lambda: int(_get_env("MAX_VOICE_BYTES", str(2 * 1024 * 1024))))
    max_photo_bytes: int = field(default_factory=lambda: int(_get_env("MAX_PHOTO_BYTES", str(10 * 1024 * 1024))))

    log_level: str = field(default_factory=lambda: _get_env("LOG_LEVEL", "INFO"))

    @property
    def webhook_url(self) -> str:
        return f"{self.webhook_base_url.rstrip('/')}{self.webhook_path}"


settings = Settings()
