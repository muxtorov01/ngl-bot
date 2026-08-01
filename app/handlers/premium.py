from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline_kb import premium_plans_kb
from app.keyboards.main_kb import back_kb
from app.repositories.plan_repo import PlanRepository
from app.repositories.user_repo import UserRepository
from app.utils.i18n import t

router = Router(name="premium")


async def show_premium_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserRepository(session)
    plans = PlanRepository(session)

    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"

    available = await plans.get_active_plans()

    text = (
        "⭐ <b>Premium obuna</b>\n\n"
        "• 📊 Batafsil statistika\n"
        "• 🔎 Kim yozganini ko‘rish\n"
        "• 🚀 Qo‘shimcha imkoniyatlar\n\n"
        "Quyidagi tariflardan birini tanlang:"
        if lang == "uz"
        else
        "⭐ <b>Premium subscription</b>\n\n"
        "• 📊 Detailed statistics\n"
        "• 🔎 Reveal sender\n"
        "• 🚀 Extra features\n\n"
        "Choose one of the plans below:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=premium_plans_kb(lang, available),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:premium")
async def cb_menu_premium(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    await show_premium_menu(callback, session)


@router.message(F.text == "⭐ Premium")
async def msg_premium(
    message: Message,
    session: AsyncSession,
) -> None:

    users = UserRepository(session)
    plans = PlanRepository(session)

    user = await users.get_by_telegram_id(message.from_user.id)
    lang = user.language if user else "en"

    available = await plans.get_active_plans()

    text = (
        "⭐ <b>Premium obuna</b>\n\n"
        "• 📊 Batafsil statistika\n"
        "• 🔎 Kim yozganini ko‘rish\n"
        "• 🚀 Qo‘shimcha imkoniyatlar\n\n"
        "Quyidagi tariflardan birini tanlang:"
        if lang == "uz"
        else
        "⭐ <b>Premium subscription</b>\n\n"
        "• 📊 Detailed statistics\n"
        "• 🔎 Reveal sender\n"
        "• 🚀 Extra features\n\n"
        "Choose one of the plans below:"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=premium_plans_kb(lang, available),
    )


@router.callback_query(F.data == "premium:back")
async def cb_premium_back(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:

    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"

    await callback.message.edit_text(
        t("main_menu", lang),
        reply_markup=back_kb(lang),
    )

    await callback.answer()
