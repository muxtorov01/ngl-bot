"""Async SQLAlchemy engine & session factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# Render/Heroku-style DATABASE_URL often starts with postgres:// -> normalize to asyncpg driver
_db_url = settings.database_url
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _db_url.startswith("postgresql://") and "+asyncpg" not in _db_url:
    _db_url = _db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(_db_url, pool_pre_ping=True, pool_size=10, max_overflow=10)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Context-managed session with commit/rollback handling."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
