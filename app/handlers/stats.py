from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline_kb import stats_menu_kb
from app.keyboards.main_kb import back_kb
from app.repositories.user_repo import UserRepository
from app.services.stats_service import StatsService
from app.utils.i18n import t
from app.utils.telegram_helpers import safe_edit_text

router = Router(name="stats")


async def _require_premium(callback: CallbackQuery, session: AsyncSession):
    users = UserRepository(session)
    user = await users.get_by_telegram_id(callback.from_user.id)
    lang = user.language if user else "en"
    if user is None or not user.is_premium_active:
        await callback.answer(t("premium_feature_locked", lang), show_alert=True)
        return None
    return user


@router.callback_query(F.data == "menu:stats")
async def cb_stats_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_premium(callback, session)
    if user is None:
        return
    await safe_edit_text(callback.message, t("stats_title", user.language), reply_markup=stats_menu_kb(user.language))
    await callback.answer()


@router.callback_query(F.data == "stats:daily")
async def cb_stats_daily(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_premium(callback, session)
    if user is None:
        return
    lang = user.language
    stats = StatsService(session)
    d = await stats.daily_stats(user.id)
    avg = f"{d['avg_response_seconds']:.0f}s" if d["avg_response_seconds"] else "—"
    text = (
        f"{t('stats_daily_title', lang)}\n\n"
        f"{t('stats_received', lang)}: {d['received']}\n"
        f"{t('stats_answered', lang)}: {d['answered']}\n"
        f"{t('stats_voice', lang)}: {d['voice_count']}\n"
        f"{t('stats_photos', lang)}: {d['photo_count']}\n"
        f"{t('stats_avg_response', lang)}: {avg}"
    )
    await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=back_kb(lang, "menu:stats"))
    await callback.answer()


@router.callback_query(F.data == "stats:weekly")
async def cb_stats_weekly(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_premium(callback, session)
    if user is None:
        return
    lang = user.language
    stats = StatsService(session)
    w = await stats.weekly_stats(user.id)
    text = (
        f"{t('stats_weekly_title', lang)}\n\n"
        f"{t('stats_total_messages', lang)}: {w['total']}\n"
        f"{t('stats_growth', lang)}: {w['growth_pct']:+.1f}%\n"
        f"{t('stats_most_active_day', lang)}: {w['most_active_day'] or '—'}\n"
        f"{t('stats_answer_rate', lang)}: {w['answer_rate']}%"
    )
    await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=back_kb(lang, "menu:stats"))
    await callback.answer()


@router.callback_query(F.data == "stats:yearly")
async def cb_stats_yearly(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_premium(callback, session)
    if user is None:
        return
    lang = user.language
    stats = StatsService(session)
    y = await stats.yearly_stats(user.id)

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    chart_lines = [f"{month_names[m - 1]}: {c}" for m, c in sorted(y["monthly_chart"].items())]
    chart = "\n".join(chart_lines) if chart_lines else t("stats_no_data", lang)
    best = month_names[y["best_month"] - 1] if y["best_month"] else "—"

    text = (
        f"{t('stats_yearly_title', lang)}\n\n"
        f"{chart}\n\n"
        f"{t('stats_total_messages', lang)}: {y['total']}\n"
        f"{t('stats_total_replies', lang)}: {y['total_replies']}\n"
        f"{t('stats_best_month', lang)}: {best}"
    )
    await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=back_kb(lang, "menu:stats"))
    await callback.answer()


@router.callback_query(F.data == "stats:top")
async def cb_stats_top(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await _require_premium(callback, session)
    if user is None:
        return
    lang = user.language
    stats = StatsService(session)
    top = await stats.top_senders(user.id)
    hours = await stats.most_active_hours(user.id)

    if top:
        lines = [
            f"{i+1}. @{tsender['username']} — {tsender['count']} msgs"
            if tsender["username"]
            else f"{i+1}. ID {tsender['telegram_id']} — {tsender['count']} msgs"
            for i, tsender in enumerate(top)
        ]
    else:
        lines = [t("no_revealable_senders", lang)]

    hours_str = ", ".join(f"{h}:00" for h in hours) if hours else "—"
    text = f"{t('top_senders_title', lang)}\n\n" + "\n".join(lines) + f"\n\n{t('most_active_hours', lang)} {hours_str}"
    await safe_edit_text(callback.message, text, parse_mode="HTML", reply_markup=back_kb(lang, "menu:stats"))
    await callback.answer()
