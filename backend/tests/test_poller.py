"""
@file test_poller.py
@description Unit and integration tests for the Steam polling and diffing engine
@module backend/tests
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.models import DailyDelta, Game, Snapshot, User
from backend.src.poller import poll_user, upsert_daily_delta
from backend.src.utils import today_utc


@pytest.mark.asyncio
async def test_first_poll_seeds_baseline_only(
    db_session: AsyncSession, sample_user: User
):
    """
    Validates that the very first observation for a game seeds the baseline snapshot
    and generates NO daily delta (enforcing the constraint: tracking starts from connection day).
    """
    mock_games = [
        {
            "appid": 730,
            "name": "Counter-Strike 2",
            "playtime_forever": 600,
            "img_icon_url": "cs2.jpg",
        }
    ]
    mock_summaries = [
        {
            "steamid": sample_user.steam_id64,
            "communityvisibilitystate": 3,
            "personaname": "Gabe",
            "avatarfull": "g.jpg",
        }
    ]

    with patch(
        "backend.src.poller.get_player_summaries",
        new=AsyncMock(return_value=mock_summaries),
    ), patch(
        "backend.src.poller.get_owned_games", new=AsyncMock(return_value=mock_games)
    ):

        res = await poll_user(db_session, sample_user)
        assert res["status"] == "success"
        assert res["games_observed"] == 1
        assert res["deltas_recorded"] == 0  # First poll seeds baseline, no delta

        # Verify snapshot was created
        snaps = (
            (
                await db_session.execute(
                    select(Snapshot).where(Snapshot.user_id == sample_user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(snaps) == 1
        assert snaps[0].playtime_forever_minutes == 600

        # Verify NO daily_delta exists
        deltas = (
            (
                await db_session.execute(
                    select(DailyDelta).where(DailyDelta.user_id == sample_user.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(deltas) == 0


@pytest.mark.asyncio
async def test_subsequent_polls_calculate_deltas_and_accumulate(
    db_session: AsyncSession, sample_user: User
):
    """
    Validates that subsequent polls calculate delta (600 -> 650 = +50 min),
    and multiple polls in the same day correctly accumulate (+50 + +30 = 80 min).
    """
    mock_summaries = [
        {
            "steamid": sample_user.steam_id64,
            "communityvisibilitystate": 3,
            "personaname": "Gabe",
            "avatarfull": "g.jpg",
        }
    ]

    with patch(
        "backend.src.poller.get_player_summaries",
        new=AsyncMock(return_value=mock_summaries),
    ):
        # Poll 1: Baseline 600 mins
        with patch(
            "backend.src.poller.get_owned_games",
            new=AsyncMock(
                return_value=[
                    {
                        "appid": 730,
                        "name": "Counter-Strike 2",
                        "playtime_forever": 600,
                        "img_icon_url": "cs2.jpg",
                    }
                ]
            ),
        ):
            await poll_user(db_session, sample_user)

        # Poll 2: Played 50 minutes (650 mins)
        with patch(
            "backend.src.poller.get_owned_games",
            new=AsyncMock(
                return_value=[
                    {
                        "appid": 730,
                        "name": "Counter-Strike 2",
                        "playtime_forever": 650,
                        "img_icon_url": "cs2.jpg",
                    }
                ]
            ),
        ):
            res2 = await poll_user(db_session, sample_user)
            assert res2["deltas_recorded"] == 1

        delta_row = (
            await db_session.execute(
                select(DailyDelta).where(
                    DailyDelta.user_id == sample_user.id, DailyDelta.app_id == 730
                )
            )
        ).scalar_one()
        assert delta_row.minutes_played == 50

        # Poll 3: Played another 30 minutes in same day (680 mins)
        with patch(
            "backend.src.poller.get_owned_games",
            new=AsyncMock(
                return_value=[
                    {
                        "appid": 730,
                        "name": "Counter-Strike 2",
                        "playtime_forever": 680,
                        "img_icon_url": "cs2.jpg",
                    }
                ]
            ),
        ):
            res3 = await poll_user(db_session, sample_user)
            assert res3["deltas_recorded"] == 1

        await db_session.refresh(delta_row)
        assert delta_row.minutes_played == 80  # 50 + 30 accumulated on same day!


@pytest.mark.asyncio
async def test_negative_delta_anomaly_does_not_corrupt_data(
    db_session: AsyncSession, sample_user: User
):
    """
    Validates that a negative playtime anomaly (e.g. Steam API glitch) is logged
    and does NOT write negative values to daily_deltas.
    """
    mock_summaries = [
        {
            "steamid": sample_user.steam_id64,
            "communityvisibilitystate": 3,
            "personaname": "Gabe",
            "avatarfull": "g.jpg",
        }
    ]

    with patch(
        "backend.src.poller.get_player_summaries",
        new=AsyncMock(return_value=mock_summaries),
    ):
        # Poll 1: Baseline 600
        with patch(
            "backend.src.poller.get_owned_games",
            new=AsyncMock(
                return_value=[
                    {
                        "appid": 730,
                        "name": "Counter-Strike 2",
                        "playtime_forever": 600,
                        "img_icon_url": "cs2.jpg",
                    }
                ]
            ),
        ):
            await poll_user(db_session, sample_user)

        # Poll 2: Played 50 min (650)
        with patch(
            "backend.src.poller.get_owned_games",
            new=AsyncMock(
                return_value=[
                    {
                        "appid": 730,
                        "name": "Counter-Strike 2",
                        "playtime_forever": 650,
                        "img_icon_url": "cs2.jpg",
                    }
                ]
            ),
        ):
            await poll_user(db_session, sample_user)

        # Poll 3: Glitched return of 620 (delta = -30)
        with patch(
            "backend.src.poller.get_owned_games",
            new=AsyncMock(
                return_value=[
                    {
                        "appid": 730,
                        "name": "Counter-Strike 2",
                        "playtime_forever": 620,
                        "img_icon_url": "cs2.jpg",
                    }
                ]
            ),
        ):
            res3 = await poll_user(db_session, sample_user)
            assert res3["deltas_recorded"] == 0

        delta_row = (
            await db_session.execute(
                select(DailyDelta).where(
                    DailyDelta.user_id == sample_user.id, DailyDelta.app_id == 730
                )
            )
        ).scalar_one()
        assert delta_row.minutes_played == 50  # Remains untouched at 50, not reduced


@pytest.mark.asyncio
async def test_private_profile_skips_game_polling(
    db_session: AsyncSession, sample_user: User
):
    """
    Validates that if profile is private (communityvisibilitystate == 1 or 2), game polling is skipped.
    """
    mock_summaries = [
        {
            "steamid": sample_user.steam_id64,
            "communityvisibilitystate": 1,
            "personaname": "PrivateUser",
            "avatarfull": "p.jpg",
        }
    ]

    with patch(
        "backend.src.poller.get_player_summaries",
        new=AsyncMock(return_value=mock_summaries),
    ), patch("backend.src.poller.get_owned_games", new=AsyncMock()) as mock_get_games:

        res = await poll_user(db_session, sample_user)
        assert res["status"] == "private_profile"
        mock_get_games.assert_not_called()
        assert sample_user.profile_visibility_state == 1
