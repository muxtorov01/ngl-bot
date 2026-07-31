from __future__ import annotations

import datetime as dt

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.message_repo import MessageRepository


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class StatsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.messages = MessageRepository(session)

    async def daily_stats(self, receiver_id: int) -> dict:
        now = _utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        data = await self.messages.stats_between(receiver_id, start, now)
        avg_response = await self.messages.average_response_seconds(receiver_id, start, now)
        return {
            "received": data["total"],
            "answered": data["answered"],
            "voice_count": data["voice"],
            "photo_count": data["photo"],
            "avg_response_seconds": avg_response,
        }

    async def weekly_stats(self, receiver_id: int) -> dict:
        now = _utcnow()
        start = now - dt.timedelta(days=7)
        prev_start = now - dt.timedelta(days=14)

        current = await self.messages.stats_between(receiver_id, start, now)
        previous = await self.messages.stats_between(receiver_id, prev_start, start)

        growth_pct = self._pct_growth(previous["total"], current["total"])
        most_active_day = self._most_active_day(current["messages"])
        answer_rate = (current["answered"] / current["total"] * 100) if current["total"] else 0.0

        return {
            "total": current["total"],
            "growth_pct": growth_pct,
            "most_active_day": most_active_day,
            "answer_rate": round(answer_rate, 1),
        }

    async def yearly_stats(self, receiver_id: int) -> dict:
        now = _utcnow()
        year = now.year
        monthly = await self.messages.monthly_counts(receiver_id, year)
        total = sum(monthly.values())

        start = dt.datetime(year, 1, 1, tzinfo=dt.timezone.utc)
        data = await self.messages.stats_between(receiver_id, start, now)
        total_replies = data["answered"]

        best_month = max(monthly, key=monthly.get) if monthly else None
        return {
            "monthly_chart": monthly,
            "total": total,
            "total_replies": total_replies,
            "best_month": best_month,
        }

    async def top_senders(self, receiver_id: int, limit: int = 5) -> list[dict]:
        rows = await self.messages.top_senders(receiver_id, limit)
        return [{"telegram_id": tid, "username": uname, "count": cnt} for tid, uname, cnt in rows]

    async def most_active_hours(self, receiver_id: int, days_back: int = 30) -> list[int]:
        now = _utcnow()
        start = now - dt.timedelta(days=days_back)
        data = await self.messages.stats_between(receiver_id, start, now)
        buckets = [0] * 24
        for m in data["messages"]:
            buckets[m.created_at.hour] += 1
        ranked = sorted(range(24), key=lambda h: buckets[h], reverse=True)
        return [h for h in ranked if buckets[h] > 0][:5]

    @staticmethod
    def _pct_growth(previous: int, current: int) -> float:
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return round((current - previous) / previous * 100, 1)

    @staticmethod
    def _most_active_day(messages: list) -> str | None:
        if not messages:
            return None
        counts: dict[str, int] = {}
        for m in messages:
            day = m.created_at.strftime("%A")
            counts[day] = counts.get(day, 0) + 1
        return max(counts, key=counts.get)


