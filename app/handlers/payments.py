from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.main_kb import main_menu_kb
from app.repositories.user_repo import UserRepository
from app.services.premium_service import PremiumService
from app.services.user_service import UserService
from app.utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="payments")


@router.callback_query(F.data.startswith("premium:buy:"))
async def cb_buy_plan(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    users = UserService(session)
    user = await users.get_or_register(callback.from_user.id, callback.from_user.username, callback.from_user.full_name)
    lang = user.language

    plan_code = callback.data.split(":", 2)[2]
    premium = PremiumService(session)
    plan = None
    for p in await premium.list_plans():
        if p.code == plan_code:
            plan = p
            break
    if plan is None:
        await callback.answer(t("plan_unavailable", lang), show_alert=True)
        return

    payment = await premium.create_pending_payment(user, plan)

    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=plan.name,
        description=t("invoice_description", lang, days=plan.duration_days),
        payload=payment.invoice_payload,
        currency="XTR",  # Telegram Stars
        prices=[LabeledPrice(label=plan.name, amount=plan.stars_price)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(pre_checkout_query.from_user.id)
    lang = user.language if user else "en"

    premium = PremiumService(session)
    payment = await premium.payments.get_by_payload(pre_checkout_query.invoice_payload)
    if payment is None:
        await pre_checkout_query.answer(ok=False, error_message=t("invoice_invalid", lang))
        return
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, session: AsyncSession) -> None:
    users = UserRepository(session)
    user_row = await users.get_by_telegram_id(message.from_user.id)
    lang = user_row.language if user_row else "en"

    sp = message.successful_payment
    premium = PremiumService(session)
    result = await premium.finalize_successful_payment(sp.invoice_payload, sp.telegram_payment_charge_id)

    if result is None:
        logger.error("Received successful_payment for unknown payload: %s", sp.invoice_payload)
        await message.answer(t("payment_unmatched", lang))
        return

    user, plan = result
    expires = user.premium_until.strftime("%Y-%m-%d %H:%M UTC") if user.premium_until else "unknown"
    await message.answer(
        t("premium_activated", lang, plan=plan.name, expires=expires),
        parse_mode="HTML",
        reply_markup=main_menu_kb(lang, True, user.is_paused, user.is_admin),
    )
