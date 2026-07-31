from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class LinkToken(TimestampMixin, Base):
    """Personal anonymous-link token. Regenerating creates a new row and
    invalidates the previous one (is_active=False), old links stop routing."""

    __tablename__ = "link_tokens"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    owner = relationship("User", back_populates="link_tokens")
