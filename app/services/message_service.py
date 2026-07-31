from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, MessageThread, MessageType, User
from app.repositories.message_repo import MessageRepository


class MessageService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.messages = MessageRepository(session)

    async def store_inbound(
        self,
        *,
        receiver: User,
        sender_telegram_id: int,
        sender_username: str | None,
        sender_full_name: str | None,
        message_type: MessageType,
        text_content: str | None = None,
        file_id: str | None = None,
        voice_duration: int | None = None,
    ) -> Message:
        thread = await self.messages.get_or_create_thread(
            receiver.id,
            sender_telegram_id,
        )

        can_reveal = receiver.is_premium_active

        message = await self.messages.add_inbound_message(
            thread=thread,
            receiver_id=receiver.id,
            sender_telegram_id=sender_telegram_id,
            sender_username=sender_username,
            sender_full_name=sender_full_name,
            message_type=message_type,
            text_content=text_content,
            file_id=file_id,
            voice_duration=voice_duration,
            can_reveal_sender=can_reveal,
        )

        return message

    async def store_reply(
        self,
        *,
        original_message: Message,
        receiver_id: int,
        message_type: MessageType,
        text_content: str | None = None,
        file_id: str | None = None,
        voice_duration: int | None = None,
    ) -> Message:
        thread = await self.session.get(
            MessageThread,
            original_message.thread_id,
        )

        reply = await self.messages.add_reply_message(
            thread=thread,
            receiver_id=receiver_id,
            sender_telegram_id=original_message.sender_telegram_id,
            message_type=message_type,
            text_content=text_content,
            file_id=file_id,
            voice_duration=voice_duration,
        )

        await self.messages.mark_answered(original_message)

        return reply

    async def find_by_delivered_message(
        self,
        receiver_id: int,
        chat_message_id: int,
    ) -> Message | None:
        return await self.messages.get_by_delivered_chat_message_id(
            receiver_id,
            chat_message_id,
        )

    async def link_delivered_message(
        self,
        message: Message,
        chat_message_id: int,
    ) -> None:
        await self.messages.set_delivered_chat_message_id(
            message,
            chat_message_id,
        )
