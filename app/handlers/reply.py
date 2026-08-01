from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.handlers.states import ReplyStates
from app.keyboards.inline_kb import cancel_kb, received_message_kb
from app.models import Message as DbMessage
from app.models import MessageDirection, MessageType
from app.repositories.moderation_repo import BlockRepository
from app.repositories.user_repo import UserRepository
from app.services.antispam_service import AntiSpamService
from app.utils.i18n import t

logger = logging.getLogger(__name__)
router = Router(name="reply")


def _reply_back_kb(thread_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(
        text="↩️ Javob yozish",
        callback_data=f"thread:{thread_id}",
    )
    return kb.as_markup()


@router.callback_query(F.data.startswith("thread:"))
async def cb_start_reply(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"

    thread_id = int(callback.data.split(":", 1)[1])

    await state.update_data(thread_id=thread_id)
    await state.set_state(ReplyStates.waiting_reply)

    await callback.message.answer(
        t("reply_prompt", lang),
        reply_markup=cancel_kb(lang),
    )

    await callback.answer()


@router.message(
    ReplyStates.waiting_reply,
    F.content_type.in_({"text", "photo", "voice"}),
)
async def handle_reply_content(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
) -> None:
    users = UserRepository(session)
    user = await users.get_by_telegram_id(message.from_user.id)
    lang = user.language if user else "en"

    data = await state.get_data()
    thread_id = data.get("thread_id")

    if thread_id is None:
        await message.answer(t("reply_session_expired", lang))
        await state.clear()
        return

    # Oxirgi xabarni olamiz
    result = await session.execute(
        select(DbMessage)
        .where(DbMessage.thread_id == thread_id)
        .order_by(DbMessage.id.desc())
        .limit(1)
    )

    last_message = result.scalar_one_or_none()

    if last_message is None:
        await message.answer(t("original_gone", lang))
        await state.clear()
        return

    # Javob kimga ketishini aniqlaymiz
    if last_message.sender_telegram_id == message.from_user.id:
        # Oxirgi xabar o'zimdan bo'lsa, qarama-qarshi tomondagi oxirgi xabarni olamiz
        result = await session.execute(
            select(DbMessage)
            .where(
                DbMessage.thread_id == thread_id,
                DbMessage.sender_telegram_id != message.from_user.id,
            )
            .order_by(DbMessage.id.desc())
            .limit(1)
        )

        target_message = result.scalar_one_or_none()
    else:
        target_message = last_message

    if target_message is None:
        await message.answer(t("original_gone", lang))
        await state.clear()
        return

    target_telegram_id = target_message.sender_telegram_id
    receiver_id = target_message.receiver_id

    message_type, text_content, file_id = _extract(message)

    if message_type is None:
        await message.answer(t("unsupported_content", lang))
        return

    # Kim yozyapti: qabul qiluvchimi (javob) yoki mehmonmi (davom etayotgan
    # anonim xabar)? Bu ikkalasi tubdan boshqa narsa va aralashtirib
    # bo'lmaydi - aks holda statistika va "kim yozdi" funksiyasi buziladi.
    is_receiver_sending = message.from_user.id == receiver_id

    if is_receiver_sending:
        direction = MessageDirection.REPLY
        can_reveal = False
        sender_username = None
        sender_full_name = None
    else:
        # Bu - mehmon tomonidan davom etayotgan anonim xabar. Birinchi
        # xabar uchun anonymous_send.py da bo'lган barcha himoya
        # tekshiruvlari shu yerda ham qo'llanishi shart.
        receiver = await users.get_by_id(receiver_id)
        if receiver is None or receiver.is_banned:
            await message.answer(t("receiver_unavailable", lang))
            await state.clear()
            return
        if receiver.is_paused:
            await message.answer(t("receiver_paused", lang))
            return

        blocks = BlockRepository(session)
        if await blocks.is_blocked(receiver_id, message.from_user.id):
            await message.answer(t("sender_blocked", lang))
            return

        size_error = _validate_guest_content(message)
        if size_error:
            await message.answer(t(size_error, lang))
            return

        antispam = AntiSpamService(session)
        dup = await antispam.check_duplicate(
            message.from_user.id, receiver_id, message.text if message.text else None
        )
        if not dup.allowed:
            await message.answer(t("duplicate_message", lang))
            return

        direction = MessageDirection.INBOUND
        # KRITIK premium qoida: faqat receiver AYNAN shu payt Premium
        # bo'lsagina, bu xabar keyinchalik ochib ko'rsatilishi mumkin.
        can_reveal = receiver.is_premium_active
        sender_username = message.from_user.username
        sender_full_name = message.from_user.full_name

    # Yangi xabarni bazaga saqlaymiz
    db_reply = DbMessage(
        thread_id=thread_id,
        receiver_id=receiver_id,
        sender_telegram_id=message.from_user.id,
        sender_username=sender_username,
        sender_full_name=sender_full_name,
        direction=direction,
        message_type=message_type,
        text_content=text_content,
        file_id=file_id,
        voice_duration=message.voice.duration if message.voice else None,
        can_reveal_sender=can_reveal,
    )

    session.add(db_reply)

    # Agar bu qabul qiluvchining javobi bo'lsa, unga sabab bo'lgan xabarni
    # "javob berilgan" deb belgilaymiz (statistika uchun kerak).
    if is_receiver_sending:
        target_message.is_answered = True

    await session.flush()

    guest = await users.get_by_telegram_id(target_telegram_id)
    guest_lang = guest.language if guest else "en"

    try:
        if is_receiver_sending:
            # Qabul qiluvchi -> mehmon: shunchaki "Javob yozish" tugmasi
            header = t("reply_header", guest_lang)
            caption = t("reply_caption", guest_lang)
            kb = _reply_back_kb(thread_id)
        else:
            # Mehmon -> qabul qiluvchi (davom etayotgan anonim xabar):
            # to'liq to'plam kerak - reply/reveal/block/report.
            header = t("new_anonymous_message", guest_lang)
            caption = header
            kb = received_message_kb(guest_lang, db_reply.id, thread_id, can_reveal)

        if message_type == MessageType.TEXT:
            body = f"{header}\n\n{text_content}"
            await bot.send_message(
                target_telegram_id,
                body,
                parse_mode="HTML",
                reply_markup=kb,
            )

        elif message_type == MessageType.PHOTO:
            await bot.send_photo(
                target_telegram_id,
                file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )

        elif message_type == MessageType.VOICE:
            await bot.send_voice(
                target_telegram_id,
                file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )

        await message.answer(t("reply_sent", lang))

    except TelegramAPIError as exc:
        logger.warning(
            "Failed to deliver reply to %s: %s",
            target_telegram_id,
            exc,
        )
        await message.answer(t("reply_delivery_failed", lang))

    await state.clear()


def _validate_guest_content(message: Message) -> str | None:
    """Same limits as the first anonymous message (anonymous_send.py) -
    returns an i18n error key, or None if the content is within limits."""
    if message.photo:
        largest = message.photo[-1]
        if largest.file_size and largest.file_size > settings.max_photo_bytes:
            return "photo_too_large"
    if message.voice:
        if message.voice.duration > settings.max_voice_seconds:
            return "voice_too_long"
        if message.voice.file_size and message.voice.file_size > settings.max_voice_bytes:
            return "voice_too_large"
    return None


def _extract(
    message: Message,
) -> tuple[MessageType | None, str | None, str | None]:
    if message.text:
        return MessageType.TEXT, message.text, None

    if message.photo:
        return MessageType.PHOTO, message.caption, message.photo[-1].file_id

    if message.voice:
        return MessageType.VOICE, None, message.voice.file_id

    return None, None, None
