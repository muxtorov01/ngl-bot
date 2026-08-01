from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.message_repo import MessageRepository
from app.repositories.moderation_repo import BlockRepository
from app.repositories.user_repo import UserRepository
from app.utils.i18n import t

router = Router(name="moderation")

# MUHIM: reveal/block tugmalari xabarning O'ZINING id'sini yuboradi
# (thread id emas) - chunki can_reveal_sender har bir xabar uchun
# alohida, shu payt qabul qiluvchining Premium holatiga qarab
# hisoblanadi. Thread id orqali "birinchi xabar"ni olish xato edi:
# suhbat davomida keyinroq kelgan (Premiumdan keyingi) xabarlar ham
# noto'g'ri ravishda "Premiumdan oldin" deb ko'rsatilardi.


@router.callback_query(F.data.startswith("reveal:"))
async def cb_reveal_sender(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"

    message_id = int(callback.data.split(":", 1)[1])
    messages = MessageRepository(session)
    msg = await messages.get_by_id(message_id)
    if msg is None or msg.receiver_id != callback.from_user.id:
        await callback.answer(t("message_not_found", lang), show_alert=True)
        return
    if not msg.can_reveal_sender:
        await callback.answer(t("reveal_locked", lang), show_alert=True)
        return

    identity = msg.sender_full_name or "Unknown"
    username_part = f" (@{msg.sender_username})" if msg.sender_username else ""
    await callback.answer(t("reveal_result", lang, identity=identity, username=username_part), show_alert=True)


@router.callback_query(F.data.startswith("block:"))
async def cb_block_sender(callback: CallbackQuery, session: AsyncSession) -> None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"

    message_id = int(callback.data.split(":", 1)[1])
    messages = MessageRepository(session)
    msg = await messages.get_by_id(message_id)
    if msg is None or msg.receiver_id != callback.from_user.id:
        await callback.answer(t("message_not_found", lang), show_alert=True)
        return

    blocks = BlockRepository(session)
    if await blocks.is_blocked(callback.from_user.id, msg.sender_telegram_id):
        await callback.answer(t("already_blocked", lang))
        return
    await blocks.block(callback.from_user.id, msg.sender_telegram_id)
    await callback.answer(t("sender_now_blocked", lang), show_alert=True)
