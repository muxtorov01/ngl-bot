from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.models import Plan
from app.utils.i18n import t


def received_message_kb(lang: str, message_id: int, can_reveal: bool = False) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=_reply_label(lang), callback_data=f"reply:{message_id}")]]
    if can_reveal:
        rows.append([InlineKeyboardButton(text=_reveal_label(lang), callback_data=f"reveal:{message_id}")])
    rows.append(
        [
            InlineKeyboardButton(text=_block_label(lang), callback_data=f"block:{message_id}"),
            InlineKeyboardButton(text=_report_label(lang), callback_data=f"report:{message_id}"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _reply_label(lang: str) -> str:
    return "↩️ Javob berish" if lang == "uz" else "↩️ Reply"


def _reveal_label(lang: str) -> str:
    return "🔎 Kim yubordi?" if lang == "uz" else "🔎 Who sent this?"


def _block_label(lang: str) -> str:
    return "🚫 Bloklash" if lang == "uz" else "🚫 Block sender"


def _report_label(lang: str) -> str:
    return "⚠️ Shikoyat" if lang == "uz" else "⚠️ Report"


def send_prompt_kb(lang: str) -> InlineKeyboardMarkup:
    label = "ℹ️ Bu qanday ishlaydi" if lang == "uz" else "ℹ️ How it works"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, callback_data="info:anonymous")]])


def premium_plans_kb(lang: str, plans: list[Plan]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{p.name} — {p.stars_price}⭐", callback_data=f"premium:buy:{p.code}")]
        for p in plans
    ]
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stats_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_stats_daily", lang), callback_data="stats:daily")],
            [InlineKeyboardButton(text=t("btn_stats_weekly", lang), callback_data="stats:weekly")],
            [InlineKeyboardButton(text=t("btn_stats_yearly", lang), callback_data="stats:yearly")],
            [InlineKeyboardButton(text=t("btn_stats_top", lang), callback_data="stats:top")],
            [InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu:home")],
        ]
    )


def report_reasons_kb(lang: str, message_id: int) -> InlineKeyboardMarkup:
    reasons = [
        ("report_reason_spam", "Spam"),
        ("report_reason_harassment", "Harassment"),
        ("report_reason_threat", "Threat"),
        ("report_reason_other", "Other"),
    ]
    rows = [
        [InlineKeyboardButton(text=t(key, lang), callback_data=f"report_reason:{message_id}:{canonical}")]
        for key, canonical in reasons
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="cancel")]])
