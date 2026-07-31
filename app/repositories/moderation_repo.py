from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Block, Broadcast, BroadcastLog, Report, ReportStatus, Setting


class BlockRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def is_blocked(self, owner_id: int, sender_telegram_id: int) -> bool:
        result = await self.session.execute(
            select(Block).where(Block.owner_id == owner_id, Block.blocked_telegram_id == sender_telegram_id)
        )
        return result.scalar_one_or_none() is not None

    async def block(self, owner_id: int, sender_telegram_id: int) -> Block:
        block = Block(owner_id=owner_id, blocked_telegram_id=sender_telegram_id)
        self.session.add(block)
        await self.session.flush()
        return block

    async def unblock(self, owner_id: int, sender_telegram_id: int) -> None:
        result = await self.session.execute(
            select(Block).where(Block.owner_id == owner_id, Block.blocked_telegram_id == sender_telegram_id)
        )
        block = result.scalar_one_or_none()
        if block:
            await self.session.delete(block)
            await self.session.flush()

    async def list_blocked(self, owner_id: int) -> list[Block]:
        result = await self.session.execute(select(Block).where(Block.owner_id == owner_id))
        return list(result.scalars().all())


class ReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, message_id: int, reporter_id: int, reason: str | None) -> Report:
        report = Report(message_id=message_id, reporter_id=reporter_id, reason=reason)
        self.session.add(report)
        await self.session.flush()
        return report

    async def list_open(self, limit: int = 20) -> list[Report]:
        result = await self.session.execute(
            select(Report).where(Report.status == ReportStatus.OPEN).order_by(Report.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def set_status(self, report: Report, status: ReportStatus) -> None:
        report.status = status
        await self.session.flush()


class BroadcastRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, created_by: int, text_content: str | None, photo_file_id: str | None, total_targets: int) -> Broadcast:
        broadcast = Broadcast(
            created_by=created_by, text_content=text_content, photo_file_id=photo_file_id, total_targets=total_targets
        )
        self.session.add(broadcast)
        await self.session.flush()
        return broadcast

    async def log_result(self, broadcast: Broadcast, user_id: int, success: bool, error: str | None) -> None:
        self.session.add(BroadcastLog(broadcast_id=broadcast.id, user_id=user_id, success=success, error=error))
        if success:
            broadcast.sent_count += 1
        else:
            broadcast.failed_count += 1
        await self.session.flush()


class SettingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str, default: str | None = None) -> str | None:
        setting = await self.session.get(Setting, key)
        return setting.value if setting else default

    async def set(self, key: str, value: str) -> None:
        setting = await self.session.get(Setting, key)
        if setting:
            setting.value = value
        else:
            self.session.add(Setting(key=key, value=value))
        await self.session.flush()
