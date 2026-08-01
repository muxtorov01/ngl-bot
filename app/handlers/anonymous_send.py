from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.handlers.states import AnonymousSendStates
from app.keyboards.inline_kb import received_message_kb
from app.models import MessageType
from app.repositories.moderation_repo import BlockRepository
from app.repositories.user_repo import UserRepository
from app.services.antispam_service import AntiSpamService
from app.services.message_service import MessageService
from app.utils.i18n import t
from app.utils.text import escape_html

logger = logging.getLogger(__name__)
router = Router(name="anonymous_send")


@router.message(
    AnonymousSendStates.waiting_message,
    F.content_type.in_({"text", "photo", "voice"}),
)
async def handle_anonymous_content(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
    bot: Bot,
    rate_limited: bool = False,
) -> None:

    users = UserRepository(session)

    guest = await users.get_by_telegram_id(message.from_user.id)

    lang = guest.language if guest else "en"

    data = await state.get_data()

    receiver_id = data.get("receiver_id")

    if receiver_id is None:
        await message.answer(t("link_session_expired", lang))
        await state.clear()
        return

    if rate_limited:
        await message.answer(t("rate_limited", lang))
        return

    receiver = await users.get_by_id(receiver_id)

    if receiver is None or receiver.is_banned:
        await message.answer(t("receiver_unavailable", lang))
        await state.clear()
        return

    if receiver.is_paused:
        await message.answer(t("receiver_paused", lang))
        await state.clear()
        return

    blocks = BlockRepository(session)

    if await blocks.is_blocked(receiver_id, message.from_user.id):
        await message.answer(t("sender_blocked", lang))
        return

    (
        message_type,
        text_content,
        file_id,
        voice_duration,
        error_key,
    ) = _extract_content(message)

    if error_key:
        await message.answer(t(error_key, lang))
        return

    antispam = AntiSpamService(session)

    dup = await antispam.check_duplicate(
        message.from_user.id,
        receiver_id,
        text_content,
    )

    if not dup.allowed:
        await message.answer(t("duplicate_message", lang))
        return

    messages_service = MessageService(session)

    stored = await messages_service.store_inbound(
        receiver=receiver,
        sender_telegram_id=message.from_user.id,
        sender_username=message.from_user.username,
        sender_full_name=message.from_user.full_name,
        message_type=message_type,
        text_content=text_content,
        file_id=file_id,
        voice_duration=voice_duration,
    )

    delivered = await _deliver_to_receiver(
        bot=bot,
        receiver_lang=receiver.language,
        receiver_telegram_id=receiver.telegram_id,
        message_type=message_type,
        text_content=text_content,
        file_id=file_id,
        thread_id=stored.thread_id,
        can_reveal=stored.can_reveal_sender,
    )

    if delivered is not None:
        await messages_service.link_delivered_message(
            stored,
            delivered.message_id,
        )

    await message.answer(t("message_delivered", lang))

    await state.clear()


def _extract_content(
    message: Message,
) -> tuple[
    MessageType | None,
    str | None,
    str | None,
    int | None,
    str | None,
]:

    if message.text:
        return MessageType.TEXT, message.text, None, None, None

    if message.photo:
        largest = message.photo[-1]

        if (
            largest.file_size
            and largest.file_size > settings.max_photo_bytes
        ):
            return None, None, None, None, "photo_too_large"

        return (
            MessageType.PHOTO,
            message.caption,
            largest.file_id,
            None,
            None,
        )

    if message.voice:

        if message.voice.duration > settings.max_voice_seconds:
            return None, None, None, None, "voice_too_long"

        if (
            message.voice.file_size
            and message.voice.file_size > settings.max_voice_bytes
        ):
            return None, None, None, None, "voice_too_large"

        return (
            MessageType.VOICE,
            None,
            message.voice.file_id,
            message.voice.duration,
            None,
        )

    return None, None, None, None, "unsupported_content"


async def _deliver_to_receiver(
    bot: Bot,
    receiver_lang: str,
    receiver_telegram_id: int,
    message_type: MessageType,
    text_content: str | None,
    file_id: str | None,
    thread_id: int,
    can_reveal: bool,
) -> Message | None:

    kb = received_message_kb(
        receiver_lang,
        thread_id,
        can_reveal,
    )

    header = t("new_anonymous_message", receiver_lang)

    try:

        if message_type == MessageType.TEXT:

            body = escape_html(text_content or "")

            return await bot.send_message(
                receiver_telegram_id,
                f"{header}\n\n{body}",
                parse_mode="HTML",
                reply_markup=kb,
            )

        if message_type == MessageType.PHOTO:

            caption = f"{header}"

            if text_content:
                caption += f"\n\n{escape_html(text_content)}"

            return await bot.send_photo(
                receiver_telegram_id,
                file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb,
            )

        if message_type == MessageType.VOICE:

            return await bot.send_voice(
                receiver_telegram_id,
                file_id,
                caption=header,
                parse_mode="HTML",
                reply_markup=kb,
            )

    except TelegramAPIError as exc:

        logger.warning(
            "Failed to deliver anonymous message to %s: %s",
            receiver_telegram_id,
            exc,
        )

    return None
