"""
@file poller.py
@description Core async polling and diffing engine with PostgreSQL advisory locking
@module backend/src
"""

from datetime import datetime, timedelta, timezone
import logging
from typing import Any
import uuid
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.config import settings
from backend.src.database import AsyncSessionLocal
from backend.src.models import DailyDelta, Game, Snapshot, User
from backend.src.steam_client import get_owned_games, get_player_summaries
from backend.src.utils import hash_user_id_for_lock, today_utc

logger = logging.getLogger(__name__)


async def acquire_user_advisory_lock(session: AsyncSession, user_id: uuid.UUID) -> bool:
    """
    Attempts to acquire a PostgreSQL transaction-level advisory lock for the user.
    Returns True if lock was acquired, False if another worker is already holding it.
    If database dialect is not PostgreSQL (e.g. SQLite in unit tests), returns True.
    """
    bind = session.bind
    if bind and "postgresql" in bind.dialect.name:
        lock_key = hash_user_id_for_lock(user_id)
        result = await session.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
            {"lock_key": lock_key},
        )
        acquired = result.scalar()
        return bool(acquired)
    return True


async def upsert_daily_delta(
    session: AsyncSession,
    user_id: uuid.UUID,
    app_id: int,
    play_date: Any,
    delta_minutes: int,
) -> None:
    """
    Upserts daily playtime delta. If an entry already exists for (user_id, app_id, play_date),
    adds delta_minutes to existing minutes_played.
    """
    bind = session.bind
    if bind and "postgresql" in bind.dialect.name:
        stmt = (
            pg_insert(DailyDelta)
            .values(
                user_id=user_id,
                app_id=app_id,
                play_date=play_date,
                minutes_played=delta_minutes,
            )
            .on_conflict_do_update(
                index_elements=["user_id", "app_id", "play_date"],
                set_={"minutes_played": DailyDelta.minutes_played + delta_minutes},
            )
        )
        await session.execute(stmt)
    else:
        # Portable fallback for SQLite/test dialects
        existing = await session.execute(
            select(DailyDelta).where(
                DailyDelta.user_id == user_id,
                DailyDelta.app_id == app_id,
                DailyDelta.play_date == play_date,
            )
        )
        delta_obj = existing.scalar_one_or_none()
        if delta_obj:
            delta_obj.minutes_played += delta_minutes
        else:
            delta_obj = DailyDelta(
                user_id=user_id,
                app_id=app_id,
                play_date=play_date,
                minutes_played=delta_minutes,
            )
            session.add(delta_obj)


async def poll_user(session: AsyncSession, user: User) -> dict[str, Any]:
    """
    Performs a full poll cycle for a single user:
    1. Acquires atomic PostgreSQL advisory lock.
    2. Refreshes player summary and profile visibility state.
    3. Fetches owned games.
    4. For each game: records raw immutable snapshot, diffs against last snapshot, and updates daily delta.
    5. Updates last_polled_at timestamp.
    """
    user_id = user.id
    steam_id64 = user.steam_id64

    # 1. Advisory lock check
    locked = await acquire_user_advisory_lock(session, user_id)
    if not locked:
        logger.info(
            "User %s is currently locked by another worker. Skipping poll tick.",
            user_id,
        )
        return {
            "status": "skipped_locked",
            "games_observed": 0,
            "deltas_recorded": 0,
        }

    # 2. Check profile visibility
    summaries = await get_player_summaries([steam_id64])
    if summaries:
        player = summaries[0]
        user.profile_visibility_state = player.get("communityvisibilitystate")
        user.persona_name = player.get("personaname", user.persona_name)
        user.avatar_url = player.get("avatarfull", user.avatar_url)

    if user.profile_visibility_state != 3:
        logger.warning(
            "User %s profile is not public (visibility_state=%s). Skipping game poll.",
            user_id,
            user.profile_visibility_state,
        )
        user.last_polled_at = datetime.now(timezone.utc)
        await session.commit()
        return {
            "status": "private_profile",
            "games_observed": 0,
            "deltas_recorded": 0,
        }

    # 3. Fetch owned games
    games = await get_owned_games(steam_id64)
    now_utc = datetime.now(timezone.utc)
    current_date = today_utc()

    deltas_recorded = 0
    games_observed = len(games)

    for game_data in games:
        app_id = game_data.get("appid")
        if not app_id:
            continue

        name = game_data.get("name", f"App {app_id}")
        icon_url = game_data.get("img_icon_url", "")
        playtime_forever = game_data.get("playtime_forever", 0)

        # Upsert game catalog info
        game_result = await session.execute(select(Game).where(Game.app_id == app_id))
        game_record = game_result.scalar_one_or_none()
        if not game_record:
            game_record = Game(app_id=app_id, name=name, icon_url=icon_url)
            session.add(game_record)
            await session.flush()
        else:
            if name and game_record.name != name:
                game_record.name = name
            if icon_url and game_record.icon_url != icon_url:
                game_record.icon_url = icon_url

        # Query the most recent snapshot prior to this one
        last_snap_res = await session.execute(
            select(Snapshot)
            .where(Snapshot.user_id == user_id, Snapshot.app_id == app_id)
            .order_by(Snapshot.captured_at.desc())
            .limit(1)
        )
        last_snapshot = last_snap_res.scalar_one_or_none()

        # Insert new raw immutable snapshot
        new_snapshot = Snapshot(
            user_id=user_id,
            app_id=app_id,
            playtime_forever_minutes=playtime_forever,
            captured_at=now_utc,
        )
        session.add(new_snapshot)
        await session.flush()

        # First observation ever for this game -> baseline seeded, no delta possible
        if last_snapshot is None:
            continue

        # Check for poll gap (>45 mins)
        last_captured = last_snapshot.captured_at
        if last_captured.tzinfo is None:
            last_captured = last_captured.replace(tzinfo=timezone.utc)
        time_diff = now_utc - last_captured
        if time_diff > timedelta(minutes=45):
            logger.warning(
                "Poll gap detected for user %s, app %d: %s elapsed between polls.",
                user_id,
                app_id,
                time_diff,
            )

        delta = playtime_forever - last_snapshot.playtime_forever_minutes
        if delta > 0:
            await upsert_daily_delta(session, user_id, app_id, current_date, delta)
            deltas_recorded += 1
        elif delta < 0:
            logger.error(
                "DATA INTEGRITY ALERT: Negative delta observed for user %s, app %d: %d minutes (previous=%d, current=%d).",
                user_id,
                app_id,
                delta,
                last_snapshot.playtime_forever_minutes,
                playtime_forever,
            )

    user.last_polled_at = now_utc
    await session.commit()

    return {
        "status": "success",
        "games_observed": games_observed,
        "deltas_recorded": deltas_recorded,
    }


async def poll_all_active_users() -> dict[str, Any]:
    """
    Polls all registered users who have a public profile or whose visibility is unknown.
    """
    logger.info("Starting batch poll tick for all active users...")
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(
                (User.profile_visibility_state == 3)
                | (User.profile_visibility_state.is_(None))
            )
        )
        users = result.scalars().all()

        total_users = len(users)
        success_count = 0
        skipped_count = 0
        error_count = 0

        for user in users:
            try:
                # Open separate sub-transaction per user so failure on one user does not abort the batch
                res = await poll_user(session, user)
                if res["status"] == "success":
                    success_count += 1
                else:
                    skipped_count += 1
            except Exception as err:
                error_count += 1
                logger.exception("Error polling user %s: %s", user.id, err)
                await session.rollback()

        logger.info(
            "Batch poll complete: total=%d, success=%d, skipped=%d, errors=%d",
            total_users,
            success_count,
            skipped_count,
            error_count,
        )
        return {
            "total_users": total_users,
            "success_count": success_count,
            "skipped_count": skipped_count,
            "error_count": error_count,
        }
