"""
@file schemas.py
@description Strict Pydantic validation schemas for API requests and responses
@module backend/src
"""

from datetime import date, datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class StrictBaseModel(BaseModel):
    """Base model enforcing extra='forbid' across all API schemas."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)


class UserRead(StrictBaseModel):
    """Public user profile data."""

    id: uuid.UUID
    steam_id64: str
    persona_name: str
    avatar_url: str
    profile_visibility_state: int | None
    connected_at: datetime
    last_polled_at: datetime | None


class TopGameInfo(StrictBaseModel):
    """Information regarding the most played game on a specific day."""

    app_id: int
    name: str
    icon_url: str
    minutes_played: int


class HeatmapDayItem(StrictBaseModel):
    """Single day entry in the heatmap."""

    date: date
    total_minutes: int
    top_game: TopGameInfo | None = None


class HeatmapResponse(StrictBaseModel):
    """Aggregated yearly contribution heatmap response."""

    user_id: uuid.UUID
    year: int
    connected_at: datetime
    total_year_minutes: int
    days: list[HeatmapDayItem]


class UserGameStat(StrictBaseModel):
    """Per-game tracked playtime statistics."""

    app_id: int
    name: str
    icon_url: str
    lifetime_tracked_minutes: int
    last_played_date: date | None = None


class UserStatus(StrictBaseModel):
    """Poll health and account status."""

    user_id: uuid.UUID
    steam_id64: str
    persona_name: str
    avatar_url: str
    profile_visibility_state: int | None
    connected_at: datetime
    last_polled_at: datetime | None
    total_games_tracked: int
    is_polling_allowed: bool
    next_poll_allowed_at: datetime | None = None


class ManualPollResponse(StrictBaseModel):
    """Result of an on-demand manual poll request."""

    success: bool
    message: str
    polled_at: datetime
    games_observed: int
    total_deltas_recorded: int


class HealthStatus(StrictBaseModel):
    """System health check and quota status."""

    status: str
    environment: str
    database_connected: bool
    steam_api_quota_daily: int
    max_supported_users: int
    registered_users_count: int
    quota_headroom_percent: float
