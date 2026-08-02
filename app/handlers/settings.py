from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.moderation_repo import BlockRepository
from app.repositories.user_repo import UserRepository
from app.utils.i18n import t
from app.utils.telegram_helpers import safe_edit_text

router = Router(name="settings")


@router.callback_query(F.data == "menu:blocks")
async def cb_blocked_list(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"
    if user is None or not user.is_premium_active:
        await callback.answer(t("blocked_feature_premium", lang), show_alert=True)
        return

    blocks = BlockRepository(session)
    blocked = await blocks.list_blocked(user.id)

    if not blocked:
        rows = [[InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu:home")]]
        await safe_edit_text(callback.message, t("no_blocked_users", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        await callback.answer()
        return

    rows = [
        [InlineKeyboardButton(text=t("unblock_btn", lang, id=b.blocked_telegram_id), callback_data=f"unblock:{b.blocked_telegram_id}")]
        for b in blocked
    ]
    rows.append([InlineKeyboardButton(text=t("btn_back", lang), callback_data="menu:home")])
    await safe_edit_text(callback.message, t("blocked_list_title", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("unblock:"))
async def cb_unblock(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id = int(callback.data.split(":", 1)[1])
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer()
        return

    blocks = BlockRepository(session)
    await blocks.unblock(user.id, target_id)
    await callback.answer(t("unblocked", user.language))
    await cb_blocked_list(callback, session)
