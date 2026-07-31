from __future__ import annotations

import enum

from sqlalchemy import BigInteger, Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MessageType(str, enum.Enum):
    TEXT = "text"
    PHOTO = "photo"
    VOICE = "voice"


class MessageDirection(str, enum.Enum):
    INBOUND = "inbound"  # guest -> receiver (anonymous)
    REPLY = "reply"      # receiver -> guest


class Message(TimestampMixin, Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    thread_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("message_threads.id", ondelete="CASCADE"), index=True)

    # receiver = the bot owner who got the anonymous message
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # sender_telegram_id is always stored internally for anti-spam / admin / reveal purposes,
    # but is only exposed to the receiver's UI when can_reveal_sender is True.
    sender_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    sender_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sender_full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    direction: Mapped[MessageDirection] = mapped_column(Enum(MessageDirection, name="message_direction"), nullable=False)
    message_type: Mapped[MessageType] = mapped_column(Enum(MessageType, name="message_type"), nullable=False)

    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_id: Mapped[str | None] = mapped_column(String(256), nullable=True)  # telegram file_id only, never local path
    voice_duration: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Delivery bookkeeping: the message_id of the copy delivered to the receiver's chat,
    # so replies (Telegram "reply to") can be mapped back to this row.
    delivered_chat_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    # CRITICAL premium logic: can this specific message's sender identity ever be revealed?
    # Set at creation time based on receiver's premium status AT THE MOMENT the message arrived.
    # Never changes afterwards -> old anonymous messages stay anonymous forever.
    can_reveal_sender: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_answered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_reported: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    receiver = relationship("User", back_populates="received_messages", foreign_keys=[receiver_id])
    thread = relationship("MessageThread", back_populates="messages")


class MessageThread(TimestampMixin, Base):
    """Groups an inbound anonymous message with all of its reply exchanges,
    so the receiver <-> guest conversation can be reconstructed."""

    __tablename__ = "message_threads"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    receiver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    sender_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    messages = relationship("Message", back_populates="thread", order_by="Message.id")
