from __future__ import annotations

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
    admin_report_actions_kb,
    confirm_broadcast_kb,
    manage_admins_kb,
)
from app.models import ReportStatus, User
from app.repositories.message_repo import MessageRepository
from app.repositories.moderation_repo import ReportRepository
from app.repositories.plan_repo import PlanRepository
from app.repositories.user_repo import UserRepository
from app.services.admin_service import AdminService
from app.services.broadcast_service import BroadcastService
from app.utils.i18n import t
from app.utils.text import escape_html

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


# ---- Reports ----

@router.callback_query(F.data == "admin:reports")
async def cb_admin_reports(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    lang = user.language
    admin = AdminService(session)
    reports = await admin.open_reports()
    if not reports:
        await callback.message.edit_text(t("no_open_reports", lang), reply_markup=admin_home_kb(lang, user.is_super_admin))
        await callback.answer()
        return

    r = reports[0]
    messages = MessageRepository(session)
    msg = await messages.get_by_id(r.message_id)
    preview = escape_html((msg.text_content or f"[{msg.message_type.value}]") if msg else "[deleted]")
    text = t("report_info", lang, id=r.id, reason=escape_html(r.reason or "—"), preview=preview, count=len(reports))
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=admin_report_actions_kb(lang, r.id, r.message_id))
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ban_from_report:"))
async def cb_admin_ban_from_report(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    lang = user.language
    report_id = int(callback.data.split(":", 2)[2])
    reports = ReportRepository(session)
    messages = MessageRepository(session)
    users = UserRepository(session)
    admin = AdminService(session)

    all_open = await reports.list_open(limit=100)
    report = next((r for r in all_open if r.id == report_id), None)
    if report is None:
        await callback.answer(t("report_not_found", lang), show_alert=True)
        return

    msg = await messages.get_by_id(report.message_id)
    if msg:
        sender = await users.get_by_telegram_id(msg.sender_telegram_id)
        if sender:
            await admin.ban_user(sender)
    await reports.set_status(report, ReportStatus.REVIEWED)
    await callback.answer(t("sender_banned", lang))
    await cb_admin_reports(callback, session)


@router.callback_query(F.data.startswith("admin:dismiss_report:"))
async def cb_admin_dismiss_report(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_admin(callback, session)
    if user is None:
        return
    lang = user.language
    report_id = int(callback.data.split(":", 2)[2])
    reports = ReportRepository(session)
    all_open = await reports.list_open(limit=100)
    report = next((r for r in all_open if r.id == report_id), None)
    if report:
        await reports.set_status(report, ReportStatus.DISMISSED)
    await callback.answer(t("dismissed", lang))
    await cb_admin_reports(callback, session)


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
