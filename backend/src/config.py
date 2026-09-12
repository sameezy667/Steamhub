"""
@file config.py
@description Application configuration and settings with Steam API capacity validation
@module backend/src
"""

import math
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings and environment configuration.
    Enforces strict configuration and calculates Steam API capacity bounds.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = Field(default="development")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://steamhub_user:steamhub_secret_password@localhost:5432/steamhub_db"
    )

    # Steam Web API & OpenID
    STEAM_API_KEY: str = Field(default="mock_steam_api_key_for_dev")
    STEAM_OPENID_REALM: str = Field(default="http://localhost:8000")
    STEAM_OPENID_RETURN_TO: str = Field(
        default="http://localhost:8000/auth/steam/callback"
    )

    # Security & Sessions
    JWT_SECRET_KEY: str = Field(
        default="dev_insecure_jwt_secret_key_32_bytes_long_change_in_prod"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRATION_DAYS: int = Field(default=30)
    CSRF_SECRET_KEY: str = Field(
        default="dev_insecure_csrf_secret_key_32_bytes_long_change_in_prod"
    )
    COOKIE_SECURE: bool = Field(default=False)
    COOKIE_NAME: str = Field(default="steamhub_session")
    NONCE_COOKIE_NAME: str = Field(default="steamhub_openid_nonce")

    # Poller Settings
    POLL_INTERVAL_MINUTES: int = Field(default=15)
    STEAM_DAILY_QUOTA: int = Field(default=100000)

    # Client Application
    FRONTEND_URL: str = Field(default="http://localhost:5173")

    @property
    def max_supported_users(self) -> int:
        """
        Calculates maximum concurrent active users allowed under Steam's daily rate limit.
        Daily requests per user = 24 * 60 / POLL_INTERVAL_MINUTES (plus 1 buffer for status/summary).
        """
        polls_per_user_day = (24 * 60) / max(1, self.POLL_INTERVAL_MINUTES)
        # Assuming 1-2 Steam API calls per poll cycle (GetPlayerSummaries + GetOwnedGames)
        calls_per_user_day = polls_per_user_day * 2
        return math.floor(self.STEAM_DAILY_QUOTA / max(1.0, calls_per_user_day))


settings = Settings()
