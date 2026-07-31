from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """Privilege level only. Premium status is tracked separately via
    `premium_until` (see is_premium_active) so a user can be Premium and
    Admin at the same time without the two concepts colliding."""

    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user id
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), default=UserRole.USER, nullable=False)

    # "uz" or "en". Set from Telegram's reported language_code on first /start,
    # user can change it anytime from Settings.
    language: Mapped[str] = mapped_column(String(2), default="en", server_default="en", nullable=False)

    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_paused: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # temp pause anon messages
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    premium_until: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    active_link_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    link_tokens = relationship("LinkToken", back_populates="owner", cascade="all, delete-orphan")
    received_messages = relationship(
        "Message", back_populates="receiver", foreign_keys="Message.receiver_id", cascade="all, delete-orphan"
    )

    @property
    def is_premium_active(self) -> bool:
        if self.premium_until is None:
            return False
        return self.premium_until > dt.datetime.now(dt.timezone.utc)

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_admin(self) -> bool:
        """True for both appointed admins and the super admin."""
        return self.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)
