from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, MessageDirection, MessageThread, MessageType


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create_thread(
        self,
        receiver_id: int,
        sender_telegram_id: int,
    ) -> MessageThread:
        result = await self.session.execute(
            select(MessageThread).where(
                MessageThread.receiver_id == receiver_id,
                MessageThread.sender_telegram_id == sender_telegram_id,
                MessageThread.is_closed.is_(False),
            )
        )

        thread = result.scalar_one_or_none()

        if thread:
            return thread

        thread = MessageThread(
            receiver_id=receiver_id,
            sender_telegram_id=sender_telegram_id,
        )

        self.session.add(thread)
        await self.session.flush()
        return thread

    async def add_inbound_message(
        self,
        *,
        thread: MessageThread,
        receiver_id: int,
        sender_telegram_id: int,
        sender_username: str | None,
        sender_full_name: str | None,
        message_type: MessageType,
        text_content: str | None,
        file_id: str | None,
        voice_duration: int | None,
        can_reveal_sender: bool,
    ) -> Message:
        msg = Message(
            thread_id=thread.id,
            receiver_id=receiver_id,
            sender_telegram_id=sender_telegram_id,
            sender_username=sender_username,
            sender_full_name=sender_full_name,
            direction=MessageDirection.INBOUND,
            message_type=message_type,
            text_content=text_content,
            file_id=file_id,
            voice_duration=voice_duration,
            can_reveal_sender=can_reveal_sender,
        )

        self.session.add(msg)
        await self.session.flush()
        return msg

    async def add_reply_message(
        self,
        *,
        thread: MessageThread,
        receiver_id: int,
        sender_telegram_id: int,
        message_type: MessageType,
        text_content: str | None,
        file_id: str | None,
        voice_duration: int | None,
    ) -> Message:
        msg = Message(
            thread_id=thread.id,
            receiver_id=receiver_id,
            sender_telegram_id=sender_telegram_id,
            direction=MessageDirection.REPLY,
            message_type=message_type,
            text_content=text_content,
            file_id=file_id,
            voice_duration=voice_duration,
            can_reveal_sender=False,
        )

        self.session.add(msg)
        await self.session.flush()
        return msg

    async def set_delivered_chat_message_id(
        self,
        message: Message,
        chat_message_id: int,
    ) -> None:
        message.delivered_chat_message_id = chat_message_id
        await self.session.flush()

    async def get_by_delivered_chat_message_id(
        self,
        receiver_id: int,
        chat_message_id: int,
    ) -> Message | None:
        result = await self.session.execute(
            select(Message).where(
                Message.receiver_id == receiver_id,
                Message.delivered_chat_message_id == chat_message_id,
            )
        )

        return result.scalar_one_or_none()

    async def get_by_id(self, message_id: int) -> Message | None:
        return await self.session.get(Message, message_id)

    # 🔥 MUHIM YANGI METOD
    async def get_first_inbound_by_thread(self, thread_id: int) -> Message | None:
        result = await self.session.execute(
            select(Message)
            .where(
                Message.thread_id == thread_id,
                Message.direction == MessageDirection.INBOUND,
            )
            .order_by(Message.id.asc())
            .limit(1)
        )

        return result.scalar_one_or_none()

    async def mark_answered(self, message: Message) -> None:
        message.is_answered = True
        await self.session.flush()

    async def mark_reported(self, message: Message) -> None:
        message.is_reported = True
        await self.session.flush()

    async def recent_identical_count(
        self,
        sender_telegram_id: int,
        receiver_id: int,
        text_content: str,
        since: dt.datetime,
    ) -> int:
        result = await self.session.execute(
            select(func.count(Message.id)).where(
                Message.sender_telegram_id == sender_telegram_id,
                Message.receiver_id == receiver_id,
                Message.text_content == text_content,
                Message.created_at >= since,
            )
        )

        return result.scalar_one()

    async def count_since(
        self,
        sender_telegram_id: int,
        since: dt.datetime,
    ) -> int:
        result = await self.session.execute(
            select(func.count(Message.id)).where(
                Message.sender_telegram_id == sender_telegram_id,
                Message.direction == MessageDirection.INBOUND,
                Message.created_at >= since,
            )
        )

        return result.scalar_one()
