"""Wave 0 async backend test harness.

Provides the fixtures every later backend test file (Plans 04 auth, 05 notes,
SEC-01 isolation) builds on:

  * ``db_session``         — a per-test transactional AsyncSession (rolled back
                             after each test => fast, fully isolated, no bleed).
  * ``app_client``         — httpx.AsyncClient over ASGITransport with
                             ``get_session`` overridden to the test session.
  * ``authed_client``      — ``app_client`` plus a freshly-inserted User and an
                             ``Authorization: Bearer <token>`` header.
  * ``other_authed_client``— a SECOND user + client, for the SEC-01 cross-user
                             404 test (Plan 05).

Test DB strategy: transaction-per-test rollback. Tables are created once per
session against ``TEST_DATABASE_URL`` (fallback ``DATABASE_URL``); each test runs
inside an outer transaction bound to a single connection and is rolled back at
teardown. This needs a reachable Postgres — when none is available locally the
DB-touching tests are exercised via ``docker compose exec backend pytest``
(Plan 08). The module itself imports without a live DB so ``pytest
--collect-only`` always succeeds.

NOTE: these fixtures import cleanly even before the auth/notes routers exist.
``authed_client`` inserts the User row and mints a token directly (via
``make_access_token``) rather than calling ``/auth/register`` so notes tests can
run in isolation regardless of plan order.
"""

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
    """Transaction-per-test session: open a connection + outer transaction, bind a
    session to it, yield, then roll back so no test leaks state into another."""
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
    """A client whose requests carry a valid Bearer token for a fresh user.

    Yields ``(client, user)`` so tests can assert ownership (SEC-01)."""
    user = await _make_user(db_session, f"user-{uuid.uuid4().hex[:8]}@test.local")
    token = make_access_token(str(user.id))
    app_client.headers["Authorization"] = f"Bearer {token}"
    yield app_client, user


@pytest_asyncio.fixture
async def other_authed_client(
    db_session: AsyncSession,
) -> AsyncGenerator[tuple[AsyncClient, User], None]:
    """A SECOND authenticated user + client for cross-user isolation tests (SEC-01).

    Uses its own AsyncClient (separate Authorization header) over the same test
    session/transaction so both users share one rolled-back DB state."""
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
