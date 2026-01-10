"""Regression test for the create-without-commit bug (Phase 01 checkpoint).

THE BUG: ``NoteRepository.create`` flushed but never committed. In production
every request gets a fresh, non-committing session from ``get_session`` — so a
``POST /notes`` returned 201 (flush assigns the id) but the row was rolled back
when the request session closed. Every subsequent ``GET``/``PATCH`` then 404'd.

WHY A SAME-SESSION ASSERTION IS INSUFFICIENT: the shared ``db_session`` harness
binds the route handler and the test to ONE connection/transaction. Within a
single transaction ``flush()`` already makes rows visible, so reading the note
back through the same session passes whether or not ``create`` commits — it
cannot distinguish flush from commit. To catch this class of bug we MUST read
back through an INDEPENDENT session on the real engine (a true session
boundary). That independent session sees the row only if ``create`` actually
committed to the database — exactly the production failure mode.

This test creates a real-engine session/user (not the rolled-back ``db_session``
harness), drives the production ``get_session`` (no override), and cleans up the
committed rows in a ``finally`` so it leaves no state behind.
"""

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
    """POST /notes must persist so an INDEPENDENT session sees the row.

    Fails (404 / row absent) if ``create`` only flushes; passes once it commits.
    Uses the real ``SessionLocal`` engine and the un-overridden production
    ``get_session`` so it exercises the true per-request session lifecycle.
    """
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
        # NO get_session override here: the route uses a real, fresh per-request
        # session, just like production.
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
