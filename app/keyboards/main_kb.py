from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.utils.i18n import t
from app.utils.text import personal_link


def main_menu_kb(lang: str, is_premium: bool, is_paused: bool, is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t("btn_my_link", lang), callback_data="menu:link")],
        [InlineKeyboardButton(text=t("btn_settings", lang), callback_data="menu:settings")],
    ]
    if is_premium:
        rows.append([InlineKeyboardButton(text=t("btn_stats", lang), callback_data="menu:stats")])
        rows.append([InlineKeyboardButton(text=t("btn_blocked", lang), callback_data="menu:blocks")])
    else:
        rows.append([InlineKeyboardButton(text=t("btn_premium", lang), callback_data="menu:premium")])
    if is_admin:
        rows.append([InlineKeyboardButton(text=t("btn_admin_panel", lang), callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def link_kb(lang: str, token: str) -> InlineKeyboardMarkup:
    url = personal_link(token)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_share_link", lang), switch_inline_query=url)],
            [InlineKeyboardButton(text=t("btn_regenerate_link", lang), callback_data="link:regenerate")],
            [InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu:home")],
        ]
    )


def settings_kb(lang: str, paused: bool, notifications: bool) -> InlineKeyboardMarkup:
    pause_label = t("btn_resume", lang) if paused else t("btn_pause", lang)
    notif_label = t("btn_notify_off", lang) if notifications else t("btn_notify_on", lang)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=pause_label, callback_data="settings:pause")],
            [InlineKeyboardButton(text=notif_label, callback_data="settings:notify")],
            [InlineKeyboardButton(text=t("btn_language", lang), callback_data="settings:language")],
            [InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu:home")],
        ]
    )


def language_kb(target: str = "menu:settings") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang:uz")],
            [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        ]
    )


def back_kb(lang: str, target: str = "menu:home") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_back", lang), callback_data=target)]])
