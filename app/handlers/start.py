from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.states import AnonymousSendStates
from app.keyboards.inline_kb import send_prompt_kb
from app.keyboards.main_kb import (
    main_menu_kb,
    language_kb,
    link_kb,
    settings_kb,
)
from app.services.user_service import UserService
from app.utils.i18n import t
from app.utils.text import escape_html, personal_link
from app.utils.telegram_helpers import safe_edit_text

logger = logging.getLogger(__name__)
router = Router(name="start")


# =========================
# /start
# =========================
@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
) -> None:

    await state.clear()

    users = UserService(session)

    user = await users.get_or_register(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
        telegram_language_code=message.from_user.language_code,
    )

    lang = user.language
    token = command.args

    # Boshqa foydalanuvchi linki ochilgan
    if token and token != user.active_link_token:

        receiver = await users.resolve_receiver_by_token(token)

        if receiver is None:
            await message.answer(t("link_invalid", lang))
            return

        if receiver.telegram_id == message.from_user.id:
            await message.answer(t("your_own_link", lang))
            return

        if receiver.is_banned:
            await message.answer(t("receiver_unavailable", lang))
            return

        if receiver.is_paused:
            await message.answer(t("receiver_paused", lang))
            return

        await state.update_data(
            receiver_id=receiver.id,
            receiver_telegram_id=receiver.telegram_id,
        )

        await state.set_state(AnonymousSendStates.waiting_message)

        name = escape_html(
            receiver.full_name
            or receiver.username
            or "this user"
        )

        await message.answer(
            t("send_prompt", lang, name=name),
            parse_mode="HTML",
            reply_markup=send_prompt_kb(lang),
        )

        return

    # Oddiy /start
    await message.answer(
        t("welcome", lang),
        reply_markup=main_menu_kb(
            lang,
            user.is_premium_active,
            user.is_paused,
            user.is_admin,
        ),
    )


# =========================
# /link
# =========================
@router.message(Command("link"))
async def cmd_link(message: Message, session: AsyncSession) -> None:

    users = UserService(session)

    user = await users.get_or_register(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    lang = user.language
    url = personal_link(user.active_link_token)

    await message.answer(
        t("your_link", lang, url=url),
        parse_mode="HTML",
        reply_markup=link_kb(lang, user.active_link_token),
    )


# =========================
# /settings
# =========================
@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession) -> None:

    users = UserService(session)

    user = await users.get_or_register(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
    )

    lang = user.language

    await message.answer(
        t("settings_title", lang),
        reply_markup=settings_kb(
            lang,
            user.is_paused,
            False,
        ),
    )


# =========================
# Back
# =========================
@router.callback_query(F.data == "menu:home")
async def cb_menu_home(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:

    await state.clear()

    users = UserService(session)

    user = await users.get_or_register(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )

    await safe_edit_text(callback.message, 
        t("welcome", user.language),
        reply_markup=main_menu_kb(
            user.language,
            user.is_premium_active,
            user.is_paused,
            user.is_admin,
        ),
    )

    await callback.answer()


# =========================
# Menu - Link
# =========================
@router.callback_query(F.data == "menu:link")
async def cb_menu_link(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:

    users = UserService(session)

    user = await users.get_or_register(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )

    lang = user.language
    url = personal_link(user.active_link_token)

    await safe_edit_text(callback.message, 
        t("your_link", lang, url=url),
        parse_mode="HTML",
        reply_markup=link_kb(lang, user.active_link_token),
    )

    await callback.answer()


# =========================
# Menu - Settings
# =========================
@router.callback_query(F.data == "menu:settings")
async def cb_menu_settings(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:

    users = UserService(session)

    user = await users.get_or_register(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )

    lang = user.language

    await safe_edit_text(callback.message, 
        t("settings_title", lang),
        reply_markup=settings_kb(
            lang,
            user.is_paused,
            False,
        ),
    )

    await callback.answer()


# =========================
# Linkni yangilash
# =========================
@router.callback_query(F.data == "link:regenerate")
async def cb_regenerate_link(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:

    users = UserService(session)

    user = await users.get_or_register(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )

    lang = user.language

    token = await users.regenerate_link(user)
    url = personal_link(token)

    await safe_edit_text(callback.message, 
        t("link_regenerated", lang, url=url),
        parse_mode="HTML",
        reply_markup=link_kb(lang, token),
    )

    await callback.answer(t("new_link_generated", lang))


# =========================
# Pause / Resume
# =========================
@router.callback_query(F.data == "settings:pause")
async def cb_toggle_pause(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:

    users = UserService(session)

    user = await users.get_or_register(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )

    lang = user.language

    user.is_paused = not bool(user.is_paused)

    await session.commit()
    await session.refresh(user)

    await safe_edit_text(callback.message, 
        t("settings_title", lang),
        reply_markup=settings_kb(
            lang,
            user.is_paused,
            False,
        ),
    )

    await callback.answer(
        "⏸ Xabarlar to‘xtatildi"
        if user.is_paused
        else "▶️ Xabarlar qayta yoqildi"
    )


# =========================
# Til tanlash
# =========================
@router.callback_query(F.data == "settings:language")
async def cb_choose_language(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:

    users = UserService(session)

    user = await users.get_or_register(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )

    await safe_edit_text(callback.message, 
        t("choose_language", user.language),
        reply_markup=language_kb(),
    )

    await callback.answer()


# =========================
# Tilni o'zgartirish
# =========================
@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:

    new_lang = callback.data.split(":", 1)[1]

    users = UserService(session)

    user = await users.get_or_register(
        callback.from_user.id,
        callback.from_user.username,
        callback.from_user.full_name,
    )

    await users.set_language(user, new_lang)

    await safe_edit_text(callback.message, 
        t("settings_title", new_lang),
        reply_markup=settings_kb(
            new_lang,
            user.is_paused,
            False,
        ),
    )

    await callback.answer(t("language_updated", new_lang))
