"""
@file test_api.py
@description Integration tests for Heatmap aggregation, Top Game window functions, and user authorization on manual polling
@module backend/tests
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
import uuid
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.config import settings
from backend.src.models import DailyDelta, Game, User
from backend.src.security import create_access_token


@pytest.mark.asyncio
async def test_health_check_endpoint(client: AsyncClient):
    """Validates health check endpoint returns 200 and capacity info."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert data["max_supported_users"] > 0


@pytest.mark.asyncio
async def test_heatmap_aggregation_and_top_game(
    client: AsyncClient, db_session: AsyncSession, sample_user: User
):
    """
    Validates heatmap aggregation across multiple games in a single day,
    correctly summing total minutes and calculating top played game via window function.
    """
    user_id = sample_user.id

    # Create two games
    g1 = Game(app_id=730, name="Counter-Strike 2", icon_url="cs2.jpg")
    g2 = Game(app_id=570, name="Dota 2", icon_url="dota2.jpg")
    db_session.add_all([g1, g2])
    await db_session.flush()

    # Day 1: 2026-06-15: CS2 (120 mins), Dota 2 (45 mins) -> Total = 165 mins, Top = CS2
    # Day 2: 2026-06-16: CS2 (30 mins), Dota 2 (90 mins) -> Total = 120 mins, Top = Dota 2
    d1 = DailyDelta(
        user_id=user_id, app_id=730, play_date=date(2026, 6, 15), minutes_played=120
    )
    d2 = DailyDelta(
        user_id=user_id, app_id=570, play_date=date(2026, 6, 15), minutes_played=45
    )
    d3 = DailyDelta(
        user_id=user_id, app_id=730, play_date=date(2026, 6, 16), minutes_played=30
    )
    d4 = DailyDelta(
        user_id=user_id, app_id=570, play_date=date(2026, 6, 16), minutes_played=90
    )
    db_session.add_all([d1, d2, d3, d4])
    await db_session.commit()

    response = await client.get(f"/api/users/{user_id}/heatmap?year=2026")
    assert response.status_code == 200
    data = response.json()

    assert data["user_id"] == str(user_id)
    assert data["year"] == 2026
    assert data["total_year_minutes"] == 285
    assert len(data["days"]) == 2

    # Day 1 check
    day1 = data["days"][0]
    assert day1["date"] == "2026-06-15"
    assert day1["total_minutes"] == 165
    assert day1["top_game"]["app_id"] == 730
    assert day1["top_game"]["name"] == "Counter-Strike 2"
    assert day1["top_game"]["minutes_played"] == 120

    # Day 2 check
    day2 = data["days"][1]
    assert day2["date"] == "2026-06-16"
    assert day2["total_minutes"] == 120
    assert day2["top_game"]["app_id"] == 570
    assert day2["top_game"]["name"] == "Dota 2"
    assert day2["top_game"]["minutes_played"] == 90


@pytest.mark.asyncio
async def test_manual_poll_requires_authentication(
    client: AsyncClient, sample_user: User
):
    """Validates that unauthenticated users cannot call POST /api/users/{id}/poll."""
    response = await client.post(f"/api/users/{sample_user.id}/poll")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_manual_poll_authorization_cross_user_forbidden(
    client: AsyncClient, db_session: AsyncSession, sample_user: User
):
    """
    Validates that user A CANNOT trigger a poll on user B's account (403 Forbidden).
    """
    user_b = User(
        id=uuid.uuid4(),
        steam_id64="76561198000000002",
        persona_name="UserB",
        profile_visibility_state=3,
    )
    db_session.add(user_b)
    await db_session.commit()

    # Authenticate as user A
    token_a = create_access_token(sample_user.id)
    client.cookies.set(settings.COOKIE_NAME, token_a)

    # User A attempts to poll User B
    response = await client.post(f"/api/users/{user_b.id}/poll")
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


@pytest.mark.asyncio
async def test_manual_poll_rate_limit_cooldown(
    client: AsyncClient, db_session: AsyncSession, sample_user: User
):
    """
    Validates that a user cannot trigger poll multiple times within the 10-minute cooldown (429).
    """
    sample_user.last_polled_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    await db_session.commit()

    token = create_access_token(sample_user.id)
    client.cookies.set(settings.COOKIE_NAME, token)

    response = await client.post(f"/api/users/{sample_user.id}/poll")
    assert response.status_code == 429
    assert "cooldown" in response.json()["detail"].lower()
    assert "Retry-After" in response.headers
