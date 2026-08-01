from __future__ import annotations

import datetime as dt
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.states import AdminBroadcastStates, AdminManageStates, AdminPriceStates
from app.keyboards.admin_kb import (
    admin_home_kb,
    admin_prices_kb,
    confirm_broadcast_kb,
    manage_admins_kb,
)
from app.models import User
from app.repositories.plan_repo import PlanRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_service import AdminService
from app.services.broadcast_service import BroadcastService
from app.utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="admin")


async def _require_admin(callback_or_msg, session: AsyncSession) -> User | None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback_or_msg.from_user.id)
    lang = user.language if user else "en"
    if user is None or not user.is_admin:
        text = t("access_denied", lang)
        if isinstance(callback_or_msg, CallbackQuery):
            await callback_or_msg.answer(text, show_alert=True)
        else:
            await callback_or_msg.answer(text)
        return None
    return user


async def _require_super_admin(callback_or_msg, session: AsyncSession) -> User | None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback_or_msg.from_user.id)
    lang = user.language if user else "en"
    if user is None or not user.is_super_admin:
        text = t("super_admin_only", lang)
        if isinstance(callback_or_msg, CallbackQuery):
            await callback_or_msg.answer(text, show_alert=True)
        else:
            await callback_or_msg.answer(text)
        return None
    return user


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    await message.answer(t("admin_panel_title", user.language), reply_markup=admin_home_kb(user.language, user.is_super_admin))


@router.callback_query(F.data == "admin:home")
async def cb_admin_home(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    await state.clear()
    await callback.message.edit_text(
        t("admin_panel_title", user.language), reply_markup=admin_home_kb(user.language, user.is_super_admin)
    )
    await callback.answer()


@router.callback_query(F.data == "admin:overview")
async def cb_admin_overview(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    lang = user.language
    admin = AdminService(session)
    data = await admin.overview()
    text = (
        f"{t('admin_overview_title', lang)}\n\n"
        f"{t('overview_total_users', lang)}: {data['total_users']}\n"
        f"{t('overview_active_7d', lang)}: {data['active_users_7d']}\n"
        f"{t('overview_premium_users', lang)}: {data['premium_users']}\n"
        f"{t('overview_revenue', lang)}: {data['revenue_stars']}⭐"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_home_kb(lang, user.is_super_admin))
    await callback.answer()


# ---- Ban / unban by command ----

@router.message(Command("ban"))
async def cmd_ban(message: Message, session: AsyncSession) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    lang = user.language
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(t("ban_usage", lang))
        return
    users = UserRepository(session)
    target = await users.get_by_telegram_id(int(parts[1]))
    if target is None:
        await message.answer(t("user_not_found", lang))
        return
    admin = AdminService(session)
    await admin.ban_user(target)
    await message.answer(t("user_banned", lang, id=target.telegram_id))


@router.message(Command("unban"))
async def cmd_unban(message: Message, session: AsyncSession) -> None:
    user = await _require_admin(message, session)
    if user is None:
        return
    lang = user.language
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(t("unban_usage", lang))
        return
    users = UserRepository(session)
    target = await users.get_by_telegram_id(int(parts[1]))
    if target is None:
        await message.answer(t("user_not_found", lang))
        return
    admin = AdminService(session)
    await admin.unban_user(target)
    await message.answer(t("user_unbanned", lang, id=target.telegram_id))


# ---- Prices ----

@router.callback_query(F.data == "admin:prices")
async def cb_admin_prices(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    lang = user.language
    plans = PlanRepository(session)
    all_plans = await plans.list_all()
    await callback.message.edit_text(t("manage_prices_title", lang), reply_markup=admin_prices_kb(lang, all_plans))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:price:"))
async def cb_admin_price_edit(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    lang = user.language
    plan_code = callback.data.split(":", 2)[2]
    await state.update_data(plan_code=plan_code)
    await state.set_state(AdminPriceStates.waiting_price)
    await callback.message.answer(t("price_prompt", lang, code=plan_code))
    await callback.answer()


@router.message(AdminPriceStates.waiting_price, F.text)
async def handle_new_price(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _require_admin(message, session)
    if user is None:
        await state.clear()
        return
    lang = user.language
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer(t("price_positive_int", lang))
        return

    data = await state.get_data()
    plan_code = data.get("plan_code")
    from app.services.premium_service import PremiumService

    premium = PremiumService(session)
    plan = await premium.update_plan_price(plan_code, int(message.text))
    await state.clear()
    if plan is None:
        await message.answer(t("plan_not_found", lang))
        return
    await message.answer(t("price_updated", lang, name=plan.name, price=plan.stars_price))


# ---- Broadcast ----

@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    await state.set_state(AdminBroadcastStates.waiting_content)
    await callback.message.answer(t("broadcast_prompt", user.language))
    await callback.answer()


@router.message(AdminBroadcastStates.waiting_content, F.content_type.in_({"text", "photo"}))
async def handle_broadcast_content(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _require_admin(message, session)
    if user is None:
        await state.clear()
        return
    lang = user.language

    if message.photo:
        await state.update_data(text_content=message.caption, photo_file_id=message.photo[-1].file_id)
        preview = message.caption or t("broadcast_no_caption", lang)
        kind = t("broadcast_kind_photo", lang)
    else:
        await state.update_data(text_content=message.text, photo_file_id=None)
        preview = message.text
        kind = t("broadcast_kind_text", lang)

    await state.set_state(AdminBroadcastStates.waiting_confirm)
    await message.answer(t("broadcast_preview", lang, kind=kind, preview=preview), reply_markup=confirm_broadcast_kb(lang))


@router.callback_query(AdminBroadcastStates.waiting_confirm, F.data == "admin:broadcast_confirm")
async def cb_admin_broadcast_confirm(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    lang = user.language
    data = await state.get_data()
    await state.clear()

    broadcast_service = BroadcastService(session)
    broadcast = await broadcast_service.create_and_run(
        bot, callback.from_user.id, data.get("text_content"), data.get("photo_file_id")
    )
    await callback.message.edit_text(
        t("broadcast_done", lang, sent=broadcast.sent_count, failed=broadcast.failed_count, total=broadcast.total_targets)
    )
    await callback.answer()


# ---- Admin management (super admin only) ----

@router.callback_query(F.data == "admin:manage_admins")
async def cb_manage_admins(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_super_admin(callback, session)
    if user is None:
        return
    lang = user.language
    admin = AdminService(session)
    admins = await admin.list_admins()
    text = t("manage_admins_title", lang) if admins else f"{t('manage_admins_title', lang)}\n\n{t('no_admins', lang)}"
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=manage_admins_kb(lang, admins))
    await callback.answer()


@router.callback_query(F.data == "admin:add_admin")
async def cb_add_admin_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    user = await _require_super_admin(callback, session)
    if user is None:
        return
    await state.set_state(AdminManageStates.waiting_admin_id)
    await callback.message.answer(t("add_admin_prompt", user.language))
    await callback.answer()


@router.message(AdminManageStates.waiting_admin_id, F.text)
async def handle_add_admin_id(message: Message, session: AsyncSession, state: FSMContext) -> None:
    user = await _require_super_admin(message, session)
    if user is None:
        await state.clear()
        return
    lang = user.language
    await state.clear()

    if not message.text.strip().lstrip("-").isdigit():
        await message.answer(t("add_admin_invalid", lang))
        return

    target_id = int(message.text.strip())
    users = UserRepository(session)
    target = await users.get_by_telegram_id(target_id)
    if target is None:
        await message.answer(t("add_admin_user_unknown", lang))
        return
    if target.is_super_admin:
        await message.answer(t("add_admin_is_super", lang))
        return
    if target.is_admin:
        await message.answer(t("add_admin_already", lang))
        return

    admin = AdminService(session)
    await admin.promote_to_admin(target)
    name = target.full_name or target.username or str(target.telegram_id)
    await message.answer(t("admin_added", lang, name=name))


@router.callback_query(F.data.startswith("admin:remove_admin:"))
async def cb_remove_admin(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_super_admin(callback, session)
    if user is None:
        return
    lang = user.language
    target_telegram_id = int(callback.data.split(":", 2)[2])

    users = UserRepository(session)
    target = await users.get_by_telegram_id(target_telegram_id)
    if target is None:
        await callback.answer(t("user_not_found", lang), show_alert=True)
        return

    admin = AdminService(session)
    await admin.demote_admin(target)
    name = target.full_name or target.username or str(target.telegram_id)
    await callback.answer(t("admin_removed", lang, name=name))
    await cb_manage_admins(callback, session)


@router.message(Command("addadmin"))
async def cmd_add_admin(message: Message, session: AsyncSession) -> None:
    user = await _require_super_admin(message, session)
    if user is None:
        return
    lang = user.language
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(t("admin_usage", lang))
        return

    users = UserRepository(session)
    target = await users.get_by_telegram_id(int(parts[1]))
    if target is None:
        await message.answer(t("add_admin_user_unknown", lang))
        return
    if target.is_super_admin:
        await message.answer(t("add_admin_is_super", lang))
        return
    if target.is_admin:
        await message.answer(t("add_admin_already", lang))
        return

    admin = AdminService(session)
    await admin.promote_to_admin(target)
    name = target.full_name or target.username or str(target.telegram_id)
    await message.answer(t("admin_added", lang, name=name))


@router.message(Command("removeadmin"))
async def cmd_remove_admin(message: Message, session: AsyncSession) -> None:
    user = await _require_super_admin(message, session)
    if user is None:
        return
    lang = user.language
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(t("removeadmin_usage", lang))
        return

    users = UserRepository(session)
    target = await users.get_by_telegram_id(int(parts[1]))
    if target is None:
        await message.answer(t("user_not_found", lang))
        return

    admin = AdminService(session)
    await admin.demote_admin(target)
    name = target.full_name or target.username or str(target.telegram_id)
    await message.answer(t("admin_removed", lang, name=name))


# ---- Free premium grant (super admin only, no payment involved) ----

@router.message(Command("grantpremium"))
async def cmd_grant_premium(message: Message, session: AsyncSession) -> None:
    user = await _require_super_admin(message, session)
    if user is None:
        return
    lang = user.language

    parts = message.text.split()
    if len(parts) != 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer(t("grantpremium_usage", lang))
        return

    target_telegram_id = int(parts[1])
    days = int(parts[2])
    if days <= 0:
        await message.answer(t("grantpremium_days_invalid", lang))
        return

    users = UserRepository(session)
    target = await users.get_by_telegram_id(target_telegram_id)
    if target is None:
        await message.answer(t("user_not_found", lang))
        return

    until = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=days)
    await users.activate_premium(target, until)

    name = target.full_name or target.username or str(target.telegram_id)
    expires = target.premium_until.strftime("%Y-%m-%d %H:%M UTC") if target.premium_until else "?"
    await message.answer(t("premium_granted", lang, name=name, days=days, expires=expires))
