"""
@file users.py
@description User endpoints for contribution heatmap, game stats, polling status, and authorized manual polling
@module backend/src/api
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.database import get_db
from backend.src.models import DailyDelta, Game, User
from backend.src.poller import poll_user
from backend.src.schemas import (
    HeatmapDayItem,
    HeatmapResponse,
    ManualPollResponse,
    TopGameInfo,
    UserGameStat,
    UserStatus,
)
from backend.src.security import get_current_user, limiter
from backend.src.utils import today_utc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get("/{user_id}/heatmap", response_model=HeatmapResponse)
async def get_user_heatmap(
    user_id: uuid.UUID,
    year: int = Query(default=2026, ge=2000, le=2100),
    db: AsyncSession = Depends(get_db),
) -> HeatmapResponse:
    """
    Returns the pre-aggregated daily playtime heatmap and top played game per day
    for the requested user and year. Single-query execution leveraging window functions.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # 1. Total minutes per day query
    totals_query = (
        select(
            DailyDelta.play_date,
            func.sum(DailyDelta.minutes_played).label("total_minutes"),
        )
        .where(
            DailyDelta.user_id == user_id,
            extract("year", DailyDelta.play_date) == year,
        )
        .group_by(DailyDelta.play_date)
    )
    totals_res = await db.execute(totals_query)
    totals_map = {row.play_date: row.total_minutes for row in totals_res.all()}

    # 2. Top game per day query using window function
    rank_col = (
        func.row_number()
        .over(
            partition_by=DailyDelta.play_date,
            order_by=desc(DailyDelta.minutes_played),
        )
        .label("rn")
    )

    ranked_subq = (
        select(
            DailyDelta.play_date,
            DailyDelta.app_id,
            DailyDelta.minutes_played,
            Game.name.label("game_name"),
            Game.icon_url.label("game_icon"),
            rank_col,
        )
        .join(Game, Game.app_id == DailyDelta.app_id)
        .where(
            DailyDelta.user_id == user_id,
            extract("year", DailyDelta.play_date) == year,
        )
        .subquery()
    )

    top_games_query = select(ranked_subq).where(ranked_subq.c.rn == 1)
    top_games_res = await db.execute(top_games_query)

    top_games_map = {
        row.play_date: TopGameInfo(
            app_id=row.app_id,
            name=row.game_name,
            icon_url=row.game_icon or "",
            minutes_played=row.minutes_played,
        )
        for row in top_games_res.all()
    }

    # Assemble days list
    days_list: list[HeatmapDayItem] = []
    total_year_minutes = 0

    for play_date, total_mins in sorted(totals_map.items()):
        total_year_minutes += total_mins
        days_list.append(
            HeatmapDayItem(
                date=play_date,
                total_minutes=total_mins,
                top_game=top_games_map.get(play_date),
            )
        )

    return HeatmapResponse(
        user_id=user.id,
        year=year,
        connected_at=user.connected_at,
        total_year_minutes=total_year_minutes,
        days=days_list,
    )


@router.get("/{user_id}/games", response_model=list[UserGameStat])
async def get_user_games(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[UserGameStat]:
    """
    Returns lifetime tracked playtime totals and last active dates per game for a user.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    query = (
        select(
            DailyDelta.app_id,
            Game.name,
            Game.icon_url,
            func.sum(DailyDelta.minutes_played).label("lifetime_minutes"),
            func.max(DailyDelta.play_date).label("last_played"),
        )
        .join(Game, Game.app_id == DailyDelta.app_id)
        .where(DailyDelta.user_id == user_id)
        .group_by(DailyDelta.app_id, Game.name, Game.icon_url)
        .order_by(desc("lifetime_minutes"))
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        UserGameStat(
            app_id=row.app_id,
            name=row.name,
            icon_url=row.icon_url or "",
            lifetime_tracked_minutes=row.lifetime_minutes or 0,
            last_played_date=row.last_played,
        )
        for row in rows
    ]


@router.get("/{user_id}/status", response_model=UserStatus)
async def get_user_status(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> UserStatus:
    """
    Returns polling health, privacy state, and game count for a user.
    """
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Count distinct games tracked in snapshots
    game_count_res = await db.execute(
        select(func.count(func.distinct(DailyDelta.app_id))).where(
            DailyDelta.user_id == user_id
        )
    )
    total_games = game_count_res.scalar() or 0

    # Determine if polling is allowed (10 minute cooldown)
    now_utc = datetime.now(timezone.utc)
    is_polling_allowed = True
    next_poll_allowed_at = None

    if user.last_polled_at:
        last_polled = user.last_polled_at
        if last_polled.tzinfo is None:
            last_polled = last_polled.replace(tzinfo=timezone.utc)
        cooldown_end = last_polled + timedelta(minutes=10)
        if now_utc < cooldown_end:
            is_polling_allowed = False
            next_poll_allowed_at = cooldown_end

    return UserStatus(
        user_id=user.id,
        steam_id64=user.steam_id64,
        persona_name=user.persona_name,
        avatar_url=user.avatar_url,
        profile_visibility_state=user.profile_visibility_state,
        connected_at=user.connected_at,
        last_polled_at=user.last_polled_at,
        total_games_tracked=total_games,
        is_polling_allowed=is_polling_allowed,
        next_poll_allowed_at=next_poll_allowed_at,
    )


@router.post("/{user_id}/poll", response_model=ManualPollResponse)
@limiter.limit("5/minute")
async def trigger_manual_poll(
    request: Request,
    user_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ManualPollResponse:
    """
    Triggers an on-demand poll for the user.
    STRICT AUTHORIZATION: Requires current session user_id to match target user_id.
    Rate-limited per user to 1 poll per 10 minutes (with 5/min IP safety guard).
    """
    if current_user.id != user_id:
        logger.warning(
            "Unauthorized poll attempt: session user %s attempted to poll user %s",
            current_user.id,
            user_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: you can only trigger polling for your own account.",
        )

    # Check 10-minute cooldown
    now_utc = datetime.now(timezone.utc)
    if current_user.last_polled_at:
        last_polled = current_user.last_polled_at
        if last_polled.tzinfo is None:
            last_polled = last_polled.replace(tzinfo=timezone.utc)
        elapsed = now_utc - last_polled
        if elapsed < timedelta(minutes=10):
            wait_seconds = int((timedelta(minutes=10) - elapsed).total_seconds())
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Poll cooldown active. Please wait {wait_seconds} seconds before polling again.",
                headers={"Retry-After": str(wait_seconds)},
            )

    poll_result = await poll_user(db, current_user)

    if poll_result["status"] == "skipped_locked":
        return ManualPollResponse(
            success=False,
            message="A background poll job is already in progress for this account.",
            polled_at=now_utc,
            games_observed=0,
            total_deltas_recorded=0,
        )

    if poll_result["status"] == "private_profile":
        return ManualPollResponse(
            success=False,
            message="Steam profile is private or game details are hidden. Set Game Details to Public to track playtime.",
            polled_at=now_utc,
            games_observed=0,
            total_deltas_recorded=0,
        )

    return ManualPollResponse(
        success=True,
        message="Poll completed successfully.",
        polled_at=now_utc,
        games_observed=poll_result.get("games_observed", 0),
        total_deltas_recorded=poll_result.get("deltas_recorded", 0),
    )
