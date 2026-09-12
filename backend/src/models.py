"""
@file models.py
@description SQLAlchemy 2.0 async models for Steamhub database schema
@module backend/src
"""

from datetime import date, datetime
import uuid
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator, CHAR


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as stringified hex.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(uuid.UUID(str(value)))
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy models."""

    pass


class User(Base):
    """
    Registered user authenticated via Steam OpenID 2.0.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    steam_id64: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True
    )
    persona_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    avatar_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    profile_visibility_state: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    last_polled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    snapshots: Mapped[list["Snapshot"]] = relationship(
        "Snapshot", back_populates="user", cascade="all, delete-orphan"
    )
    daily_deltas: Mapped[list["DailyDelta"]] = relationship(
        "DailyDelta", back_populates="user", cascade="all, delete-orphan"
    )


class Game(Base):
    """
    Catalog of Steam games identified by app_id.
    """

    __tablename__ = "games"

    app_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # Relationships
    snapshots: Mapped[list["Snapshot"]] = relationship(
        "Snapshot", back_populates="game"
    )
    daily_deltas: Mapped[list["DailyDelta"]] = relationship(
        "DailyDelta", back_populates="game"
    )


class Snapshot(Base):
    """
    Raw immutable audit log of observed playtime per user and game.
    Never update, never delete.
    """

    __tablename__ = "snapshots"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    app_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.app_id", ondelete="CASCADE"),
        nullable=False,
    )
    playtime_forever_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="snapshots")
    game: Mapped["Game"] = relationship("Game", back_populates="snapshots")

    __table_args__ = (
        Index(
            "idx_snapshots_user_app_time",
            "user_id",
            "app_id",
            captured_at.desc(),
        ),
    )


class DailyDelta(Base):
    """
    Derived, rebuildable aggregate of playtime minutes played per day.
    Rebuildable from raw snapshots at any time via backfill script.
    """

    __tablename__ = "daily_deltas"

    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    app_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("games.app_id", ondelete="CASCADE"),
        primary_key=True,
    )
    play_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
    )
    minutes_played: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="daily_deltas")
    game: Mapped["Game"] = relationship("Game", back_populates="daily_deltas")

    __table_args__ = (
        Index(
            "idx_daily_deltas_user_date_minutes",
            "user_id",
            "play_date",
            minutes_played.desc(),
        ),
    )
