from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.states import AnonymousSendStates
from app.keyboards.inline_kb import send_prompt_kb
from app.keyboards.main_kb import language_kb, link_kb, main_menu_kb, settings_kb
from app.services.user_service import UserService
from app.utils.i18n import t
from app.utils.text import escape_html, personal_link

logger = logging.getLogger(__name__)
router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession, state: FSMContext) -> None:
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

    if token and token != user.active_link_token:
        # A guest opened someone else's personal link.
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

        await state.update_data(receiver_id=receiver.id, receiver_telegram_id=receiver.telegram_id)
        await state.set_state(AnonymousSendStates.waiting_message)

        name = escape_html(receiver.full_name or receiver.username or "this user")
        await message.answer(
            t("send_prompt", lang, name=name),
            parse_mode="HTML",
            reply_markup=send_prompt_kb(lang),
        )
        return

    # Plain /start — show the owner their own menu.
    await message.answer(
        t("welcome", lang),
        reply_markup=main_menu_kb(lang, user.is_premium_active, user.is_paused, user.is_admin),
    )


@router.callback_query(F.data == "menu:home")
async def cb_menu_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    await callback.message.edit_text(
        t("main_menu", lang),
        reply_markup=main_menu_kb(lang, user.is_premium_active, user.is_paused, user.is_admin),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:link")
async def cb_menu_link(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    url = personal_link(user.active_link_token)
    await callback.message.edit_text(
        t("your_link", lang, url=url),
        parse_mode="HTML",
        reply_markup=link_kb(lang, user.active_link_token),
    )
    await callback.answer()


@router.callback_query(F.data == "link:regenerate")
async def cb_regenerate_link(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    token = await users.regenerate_link(user)
    url = personal_link(token)
    await callback.message.edit_text(
        t("link_regenerated", lang, url=url),
        parse_mode="HTML",
        reply_markup=link_kb(lang, token),
    )
    await callback.answer(t("new_link_generated", lang))


@router.callback_query(F.data == "menu:settings")
async def cb_menu_settings(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    await callback.message.edit_text(
        t("settings_title", lang),
        reply_markup=settings_kb(lang, user.is_paused, user.notifications_enabled),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:pause")
async def cb_toggle_pause(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    paused = await users.toggle_pause(user)
    await callback.message.edit_text(
        t("settings_title", lang),
        reply_markup=settings_kb(lang, paused, user.notifications_enabled),
    )
    await callback.answer(t("messages_paused", lang) if paused else t("messages_resumed", lang))


@router.callback_query(F.data == "settings:notify")
async def cb_toggle_notify(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    enabled = await users.toggle_notifications(user)
    await callback.message.edit_text(
        t("settings_title", lang),
        reply_markup=settings_kb(lang, user.is_paused, enabled),
    )
    await callback.answer(t("notifications_on", lang) if enabled else t("notifications_off", lang))


@router.callback_query(F.data == "settings:language")
async def cb_choose_language(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    await callback.message.edit_text(t("choose_language", lang), reply_markup=language_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(callback: CallbackQuery, session: AsyncSession) -> None:
    new_lang = callback.data.split(":", 1)[1]
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    await users.set_language(user, new_lang)
    await callback.message.edit_text(
        t("settings_title", new_lang),
        reply_markup=settings_kb(new_lang, user.is_paused, user.notifications_enabled),
    )
    await callback.answer(t("language_updated", new_lang))


@router.callback_query(F.data == "info:anonymous")
async def cb_info_anonymous(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    await callback.answer(t("info_anonymous", user.language), show_alert=True)


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language
    await callback.message.edit_text(
        t("cancelled", lang),
        reply_markup=main_menu_kb(lang, user.is_premium_active, user.is_paused, user.is_admin),
    )
    await callback.answer()
