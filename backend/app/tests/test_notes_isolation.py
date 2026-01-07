"""SEC-01 — the REQUIRED cross-user isolation test.

User A creates a note; user B (a different authenticated user) must get **404**
on GET, PATCH, and DELETE of A's note (404, not 403, so existence is never
leaked — T-05-01/T-05-02), and A's data must be unaffected. An unauthenticated
request gets 401 (T-05-03).

Uses ``authed_client`` (user A) + ``other_authed_client`` (user B), which share
one rolled-back transaction so both users see the same DB state.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.main import app
from app.models import User


@pytest.mark.asyncio
async def test_isolation_get(
    authed_client: tuple[AsyncClient, User],
    other_authed_client: tuple[AsyncClient, User],
) -> None:
    """User B GET of A's note -> 404 (SEC-01)."""
    client_a, _user_a = authed_client
    client_b, _user_b = other_authed_client

    a_note = (await client_a.post("/notes", json={"title": "A-secret"})).json()
    resp = await client_b.get(f"/notes/{a_note['id']}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_isolation_patch(
    authed_client: tuple[AsyncClient, User],
    other_authed_client: tuple[AsyncClient, User],
) -> None:
    """User B PATCH of A's note -> 404, and A's note is unchanged (SEC-01)."""
    client_a, _user_a = authed_client
    client_b, _user_b = other_authed_client

    a_note = (await client_a.post("/notes", json={"title": "A-secret"})).json()
    resp = await client_b.patch(f"/notes/{a_note['id']}", json={"title": "hacked"})
    assert resp.status_code == 404

    # A still sees the original title.
    reopened = await client_a.get(f"/notes/{a_note['id']}")
    assert reopened.status_code == 200
    assert reopened.json()["title"] == "A-secret"


@pytest.mark.asyncio
async def test_isolation_delete(
    authed_client: tuple[AsyncClient, User],
    other_authed_client: tuple[AsyncClient, User],
) -> None:
    """User B DELETE of A's note -> 404, and A's note still listed for A (SEC-01)."""
    client_a, _user_a = authed_client
    client_b, _user_b = other_authed_client

    a_note = (await client_a.post("/notes", json={"title": "A-secret"})).json()
    resp = await client_b.delete(f"/notes/{a_note['id']}")
    assert resp.status_code == 404

    # A's note survives.
    listed_ids = [n["id"] for n in (await client_a.get("/notes")).json()]
    assert a_note["id"] in listed_ids


@pytest.mark.asyncio
async def test_unauthenticated(db_session: AsyncSession) -> None:
    """Any /notes call without a token -> 401 (T-05-03)."""

    async def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/notes")).status_code == 401
        assert (await client.post("/notes", json={})).status_code == 401
    app.dependency_overrides.pop(get_session, None)
