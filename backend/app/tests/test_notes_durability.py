"""Regression test for the create-without-commit bug: reads back through an INDEPENDENT real-engine session (a true session boundary) since a same-session flush can't be distinguished from a commit."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.core.security import hash_password, make_access_token
from app.main import app
from app.models import Page, User


@pytest.mark.asyncio
async def test_create_is_durable_across_session_boundary(engine) -> None:
    """POST /notes must persist so an INDEPENDENT session sees the row (fails if ``create`` only flushes); uses the real engine and un-overridden ``get_session``."""
    # A committed user on the real engine (the production session must find it).
    email = f"durable-{uuid.uuid4().hex[:8]}@test.local"
    async with SessionLocal() as setup:
        user = User(email=email, hashed_password=hash_password("password123"))
        setup.add(user)
        await setup.commit()
        await setup.refresh(user)
        user_id = user.id

    token = make_access_token(str(user_id))
    note_id: str | None = None
    try:
        # NO get_session override here: the route uses a real, fresh per-request session like production.
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as client:
            created = await client.post(
                "/notes",
                json={"title": "Durable", "content": {"type": "doc", "content": []}},
            )
            assert created.status_code == 201
            note_id = created.json()["id"]

            # A SEPARATE HTTP request => a SEPARATE session. 404 here is the bug.
            fetched = await client.get(f"/notes/{note_id}")
            assert fetched.status_code == 200, "created note must survive the session boundary"
            assert fetched.json()["title"] == "Durable"

        # And prove it at the DB layer through a fully independent session.
        async with SessionLocal() as verify:
            row = (
                await verify.execute(select(Page).where(Page.id == uuid.UUID(note_id)))
            ).scalar_one_or_none()
            assert row is not None, "row must be committed, not just flushed"
    finally:
        # This test commits real rows; clean them up so it leaves no state.
        async with SessionLocal() as cleanup:
            if note_id is not None:
                await cleanup.execute(delete(Page).where(Page.id == uuid.UUID(note_id)))
            await cleanup.execute(delete(User).where(User.id == user_id))
            await cleanup.commit()
