from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import Plan, User
from app.utils.i18n import t


def admin_home_kb(lang: str, is_super_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t("btn_admin_overview", lang), callback_data="admin:overview")],
        [InlineKeyboardButton(text=t("btn_admin_broadcast", lang), callback_data="admin:broadcast")],
        [InlineKeyboardButton(text=t("btn_admin_prices", lang), callback_data="admin:prices")],
    ]
    if is_super_admin:
        rows.append([InlineKeyboardButton(text=t("btn_admin_manage_admins", lang), callback_data="admin:manage_admins")])
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_prices_kb(lang: str, plans: list[Plan]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.name}: {p.stars_price}⭐ ✏️", callback_data=f"admin:price:{p.code}")]
        for p in plans
    ]
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_broadcast_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_send_now", lang), callback_data="admin:broadcast_confirm")],
            [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="admin:home")],
        ]
    )


def manage_admins_kb(lang: str, admins: list[User]) -> InlineKeyboardMarkup:
    rows = []
    for admin in admins:
        name = admin.full_name or admin.username or str(admin.telegram_id)
        rows.append(
            [InlineKeyboardButton(text=t("btn_remove_admin", lang, name=name), callback_data=f"admin:remove_admin:{admin.telegram_id}")]
        )
    rows.append([InlineKeyboardButton(text=t("btn_add_admin", lang), callback_data="admin:add_admin")])
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
