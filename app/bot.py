"""Application entrypoint: builds the aiogram Bot/Dispatcher and runs it in
webhook mode behind an aiohttp web server, as required for Render.com."""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, MenuButtonCommands
from aiogram.webhook.aiohttp_server import (
    SimpleRequestHandler,
    setup_application,
)
from aiohttp import web

from app.config import settings
from app.db import get_session
from app.handlers import (
    admin,
    anonymous_send,
    payments,
    premium,
    reply,
    reports,
    settings as settings_handlers,
    start,
    stats,
)
from app.middlewares.db_middleware import DbSessionMiddleware
from app.middlewares.throttling import ThrottlingMiddleware
from app.repositories.plan_repo import PlanRepository
from app.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()

    # Order matters
    dp.update.middleware(DbSessionMiddleware())
    dp.message.middleware(ThrottlingMiddleware())

    # Routers
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(premium.router)
    dp.include_router(payments.router)
    dp.include_router(stats.router)
    dp.include_router(settings_handlers.router)
    dp.include_router(reports.router)
    dp.include_router(reply.router)
    dp.include_router(anonymous_send.router)

    return dp


async def _seed_defaults() -> None:
    async with get_session() as session:
        plans = PlanRepository(session)
        await plans.ensure_defaults()


# 👇 KICHIK ☰ MENU TUGMASI
async def setup_menu(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Asosiy menyu"),
        BotCommand(command="link", description="Mening anonim linkim"),
        BotCommand(command="premium", description="Premium"),
        BotCommand(command="settings", description="Sozlamalar"),
    ])

    await bot.set_chat_menu_button(
        menu_button=MenuButtonCommands()
    )

    logger.info("Chat menu button configured")


async def on_startup(bot: Bot) -> None:
    await _seed_defaults()

    # 👇 MENU O'RNATILADI
    await setup_menu(bot)

    await bot.set_webhook(
        url=settings.webhook_url,
        secret_token=settings.webhook_secret,
        allowed_updates=[
            "message",
            "callback_query",
            "pre_checkout_query",
        ],
        drop_pending_updates=True,
    )

    logger.info("Webhook set to %s", settings.webhook_url)


async def on_shutdown(bot: Bot) -> None:
    await bot.delete_webhook()
    logger.info("Webhook removed, shutting down.")


def main() -> None:
    setup_logging()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = create_dispatcher()

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
        secret_token=settings.webhook_secret,
    ).register(app, path=settings.webhook_path)

    setup_application(app, dp, bot=bot)

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app.router.add_get("/health", health)

    web.run_app(
        app,
        host=settings.web_server_host,
        port=settings.web_server_port,
    )


if __name__ == "__main__":
    main()
