"""Async backend test harness: transaction-per-test ``db_session`` (rolled back) plus ``app_client``/``authed_client``/``other_authed_client`` fixtures; needs a reachable Postgres but imports/collects without one."""

import os
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.db import Base, get_session
from app.core.security import hash_password, make_access_token
from app.main import app
from app.models import User

# Prefer a dedicated test database; fall back to the primary DATABASE_URL.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or os.environ["DATABASE_URL"]


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Session-scoped async engine; creates the schema once, drops it at the end."""
    eng = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Transaction-per-test session: bind to an outer transaction, yield, then roll back so no test leaks state."""
    async with engine.connect() as connection:
        trans = await connection.begin()
        session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
        session = session_factory()
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest_asyncio.fixture
async def app_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """ASGI client with get_session overridden to the transactional test session."""

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.pop(get_session, None)


async def _make_user(db_session: AsyncSession, email: str) -> User:
    user = User(email=email.lower(), hashed_password=hash_password("password123"))
    db_session.add(user)
    await db_session.flush()  # populate user.id without committing the outer transaction
    return user


@pytest_asyncio.fixture
async def authed_client(
    app_client: AsyncClient, db_session: AsyncSession
) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """A client carrying a valid Bearer token for a fresh user; yields ``(client, user)`` so tests can assert ownership (SEC-01)."""
    user = await _make_user(db_session, f"user-{uuid.uuid4().hex[:8]}@test.local")
    token = make_access_token(str(user.id))
    app_client.headers["Authorization"] = f"Bearer {token}"
    yield app_client, user


@pytest_asyncio.fixture
async def other_authed_client(
    db_session: AsyncSession,
) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """A SECOND authenticated user + client (own Authorization header, same test transaction) for cross-user isolation tests (SEC-01)."""
    user = await _make_user(db_session, f"other-{uuid.uuid4().hex[:8]}@test.local")
    token = make_access_token(str(user.id))

    async def _override_get_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as client:
        yield client, user
    app.dependency_overrides.pop(get_session, None)


# Backwards/forwards-compatible alias: some tests refer to the second user fixture.
@pytest.fixture
def second_user_client(other_authed_client):
    return other_authed_client
