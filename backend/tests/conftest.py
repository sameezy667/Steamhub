"""
@file conftest.py
@description Pytest configuration, async test database fixtures, and API test client
@module backend/tests
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import uuid
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from backend.src.database import get_db
from backend.src.main import app
from backend.src.models import Base, Game, User

# In-memory SQLite async engine for isolated testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(autouse=True)
async def init_test_database():
    """Initializes schema before every test and cleans up after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields an isolated database session for testing."""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP test client with database dependency override."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_user(db_session: AsyncSession) -> User:
    """Creates a sample test user with a public profile."""
    user = User(
        id=uuid.uuid4(),
        steam_id64="76561198000000001",
        persona_name="GabeFollower",
        avatar_url="https://avatars.steamstatic.com/test_avatar.jpg",
        profile_visibility_state=3,
        connected_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_game(db_session: AsyncSession) -> Game:
    """Creates a sample test game."""
    game = Game(
        app_id=730,
        name="Counter-Strike 2",
        icon_url="https://media.steampowered.com/cs2.jpg",
    )
    db_session.add(game)
    await db_session.commit()
    return game
