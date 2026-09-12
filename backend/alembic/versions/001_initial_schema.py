"""
@file 001_initial_schema.py
@description Initial database schema migration
@module backend/alembic/versions
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users Table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("steam_id64", sa.String(length=32), nullable=False),
        sa.Column(
            "persona_name", sa.String(length=255), nullable=False, server_default=""
        ),
        sa.Column(
            "avatar_url", sa.String(length=512), nullable=False, server_default=""
        ),
        sa.Column("profile_visibility_state", sa.Integer(), nullable=True),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_users_steam_id64"), "users", ["steam_id64"], unique=True)

    # Games Table
    op.create_table(
        "games",
        sa.Column("app_id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("icon_url", sa.String(length=512), nullable=False, server_default=""),
    )

    # Snapshots Table
    op.create_table(
        "snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "app_id",
            sa.Integer(),
            sa.ForeignKey("games.app_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("playtime_forever_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_snapshots_user_app_time",
        "snapshots",
        ["user_id", "app_id", sa.text("captured_at DESC")],
    )

    # Daily Deltas Table
    op.create_table(
        "daily_deltas",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "app_id",
            sa.Integer(),
            sa.ForeignKey("games.app_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("play_date", sa.Date(), primary_key=True),
        sa.Column("minutes_played", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "idx_daily_deltas_user_date_minutes",
        "daily_deltas",
        ["user_id", "play_date", sa.text("minutes_played DESC")],
    )


def downgrade() -> None:
    op.drop_table("daily_deltas")
    op.drop_table("snapshots")
    op.drop_table("games")
    op.drop_table("users")
