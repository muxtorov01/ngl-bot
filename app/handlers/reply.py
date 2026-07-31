from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from app.handlers.states import ReplyStates
from app.keyboards.inline_kb import cancel_kb
from app.models import MessageType
from app.repositories.message_repo import MessageRepository
from app.repositories.user_repo import UserRepository
from app.services.message_service import MessageService
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

    messages_repo = MessageRepository(session)

    original = await messages_repo.get_first_inbound_by_thread(thread_id)

    if original is None:
        await message.answer(t("original_gone", lang))
        await state.clear()
        return

    message_type, text_content, file_id = _extract(message)

    if message_type is None:
        await message.answer(t("unsupported_content", lang))
        return

    messages_service = MessageService(session)

    await messages_service.store_reply(
        original_message=original,
        receiver_id=message.from_user.id,
        message_type=message_type,
        text_content=text_content,
        file_id=file_id,
        voice_duration=message.voice.duration if message.voice else None,
    )

    guest = await users.get_by_telegram_id(original.sender_telegram_id)
    guest_lang = guest.language if guest else "en"

    try:
        if message_type == MessageType.TEXT:
            await bot.send_message(
                original.sender_telegram_id,
                f"{t('reply_header', guest_lang)}\n\n{text_content}",
                parse_mode="HTML",
                reply_markup=_reply_back_kb(thread_id),
            )

        elif message_type == MessageType.PHOTO:
            await bot.send_photo(
                original.sender_telegram_id,
                file_id,
                caption=t("reply_caption", guest_lang),
                reply_markup=_reply_back_kb(thread_id),
            )

        elif message_type == MessageType.VOICE:
            await bot.send_voice(
                original.sender_telegram_id,
                file_id,
                caption=t("reply_caption", guest_lang),
                reply_markup=_reply_back_kb(thread_id),
            )

        await message.answer(t("reply_sent", lang))

    except TelegramAPIError as exc:
        logger.warning(
            "Failed to deliver reply to %s: %s",
            original.sender_telegram_id,
            exc,
        )
        await message.answer(t("reply_delivery_failed", lang))

    await state.clear()


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
