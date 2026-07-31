from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline_kb import premium_plans_kb
from app.repositories.user_repo import UserRepository
from app.services.premium_service import PremiumService
from app.utils.i18n import t

router = Router(name="premium")


@router.callback_query(F.data == "menu:premium")
async def cb_premium_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"

    premium = PremiumService(session)
    plans = await premium.list_plans()
    if not plans:
        await callback.answer(t("premium_not_configured", lang), show_alert=True)
        return

    await callback.message.edit_text(t("premium_plans_header", lang), parse_mode="HTML", reply_markup=premium_plans_kb(lang, plans))
    await callback.answer()
