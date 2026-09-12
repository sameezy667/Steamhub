"""
@file test_backfill.py
@description Unit tests validating that the backfill script rebuilds daily_deltas matching incremental polling parity
@module backend/tests
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.backfill import recompute_daily_deltas_for_user
from backend.src.models import DailyDelta, Game, Snapshot, User


@pytest.mark.asyncio
async def test_backfill_matches_incremental_polling_parity(
    db_session: AsyncSession, sample_user: User, sample_game: Game
):
    """
    Seeds raw snapshots simulating 3 days of gaming, executes the backfill rebuild script,
    and asserts that daily_deltas are computed accurately.
    """
    user_id = sample_user.id
    app_id = sample_game.app_id

    # Day 1: Baseline snapshot at 10:00 (100 min) -> Played at 18:00 (150 min -> +50) -> Played at 21:00 (190 min -> +40) [Day 1 total = 90 min]
    s1 = Snapshot(
        user_id=user_id,
        app_id=app_id,
        playtime_forever_minutes=100,
        captured_at=datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
    )
    s2 = Snapshot(
        user_id=user_id,
        app_id=app_id,
        playtime_forever_minutes=150,
        captured_at=datetime(2026, 6, 1, 18, 0, tzinfo=timezone.utc),
    )
    s3 = Snapshot(
        user_id=user_id,
        app_id=app_id,
        playtime_forever_minutes=190,
        captured_at=datetime(2026, 6, 1, 21, 0, tzinfo=timezone.utc),
    )

    # Day 2: Played at 14:00 (300 min -> +110 min) [Day 2 total = 110 min]
    s4 = Snapshot(
        user_id=user_id,
        app_id=app_id,
        playtime_forever_minutes=300,
        captured_at=datetime(2026, 6, 2, 14, 0, tzinfo=timezone.utc),
    )

    # Day 3: No play observed (300 min -> +0 min)
    s5 = Snapshot(
        user_id=user_id,
        app_id=app_id,
        playtime_forever_minutes=300,
        captured_at=datetime(2026, 6, 3, 10, 0, tzinfo=timezone.utc),
    )

    db_session.add_all([s1, s2, s3, s4, s5])
    await db_session.commit()

    # Run backfill
    stats = await recompute_daily_deltas_for_user(db_session, user_id, dry_run=False)
    assert stats["snapshots_processed"] == 5
    assert stats["deltas_generated"] == 3
    assert stats["delta_rows"] == 2  # Day 1 and Day 2

    # Query daily_deltas from database
    deltas = (
        (
            await db_session.execute(
                select(DailyDelta)
                .where(DailyDelta.user_id == user_id)
                .order_by(DailyDelta.play_date.asc())
            )
        )
        .scalars()
        .all()
    )

    assert len(deltas) == 2
    assert deltas[0].play_date.isoformat() == "2026-06-01"
    assert deltas[0].minutes_played == 90

    assert deltas[1].play_date.isoformat() == "2026-06-02"
    assert deltas[1].minutes_played == 110
