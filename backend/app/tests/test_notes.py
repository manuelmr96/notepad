"""NOTE-01..05 owner-lifecycle tests for the /notes API (create/list, open/partial-edit, sort, soft-delete D-13); needs Postgres but collects without one."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Page, User


@pytest.mark.asyncio
async def test_create_and_list(authed_client: tuple[AsyncClient, User]) -> None:
    """NOTE-01/02: POST creates (201) and the note appears in the owner's list."""
    client, _user = authed_client

    resp = await client.post(
        "/notes", json={"title": "First", "content": {"type": "doc", "content": []}}
    )
    assert resp.status_code == 201
    created = resp.json()
    assert created["title"] == "First"
    assert created["content_schema_version"] == 1
    note_id = created["id"]

    listed = await client.get("/notes")
    assert listed.status_code == 200
    ids = [n["id"] for n in listed.json()]
    assert note_id in ids


@pytest.mark.asyncio
async def test_create_defaults_empty_doc(authed_client: tuple[AsyncClient, User]) -> None:
    """D-05 instant-create: POST with no body yields an empty editor doc + empty title."""
    client, _user = authed_client
    resp = await client.post("/notes", json={})
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == ""
    assert body["content"] == {"type": "doc", "content": []}


@pytest.mark.asyncio
async def test_open_and_edit(authed_client: tuple[AsyncClient, User]) -> None:
    """NOTE-03/04: open returns 200; partial PATCH updates only the given field."""
    client, _user = authed_client
    created = (
        await client.post(
            "/notes", json={"title": "Original", "content": {"type": "doc", "content": [{"x": 1}]}}
        )
    ).json()
    note_id = created["id"]

    opened = await client.get(f"/notes/{note_id}")
    assert opened.status_code == 200
    assert opened.json()["title"] == "Original"

    # PATCH title only -> content untouched (partial autosave).
    r1 = await client.patch(f"/notes/{note_id}", json={"title": "Renamed"})
    assert r1.status_code == 200
    assert r1.json()["title"] == "Renamed"
    assert r1.json()["content"] == {"type": "doc", "content": [{"x": 1}]}

    # PATCH content only -> title untouched.
    new_content = {"type": "doc", "content": [{"y": 2}]}
    r2 = await client.patch(f"/notes/{note_id}", json={"content": new_content})
    assert r2.status_code == 200
    assert r2.json()["content"] == new_content
    assert r2.json()["title"] == "Renamed"


@pytest.mark.asyncio
async def test_empty_patch_is_noop(authed_client: tuple[AsyncClient, User]) -> None:
    """NOTE-04/06: an empty PATCH body is idempotent (no field changes)."""
    client, _user = authed_client
    created = (
        await client.post(
            "/notes", json={"title": "Keep", "content": {"type": "doc", "content": []}}
        )
    ).json()
    note_id = created["id"]
    r = await client.patch(f"/notes/{note_id}", json={})
    assert r.status_code == 200
    assert r.json()["title"] == "Keep"


@pytest.mark.asyncio
async def test_list_sort(authed_client: tuple[AsyncClient, User]) -> None:
    """List is most-recently-updated first: editing the older note floats it to top."""
    client, _user = authed_client
    a = (await client.post("/notes", json={"title": "A"})).json()
    b = (await client.post("/notes", json={"title": "B"})).json()

    # Edit A (the older one) so its updated_at becomes the newest.
    await client.patch(f"/notes/{a['id']}", json={"title": "A-edited"})

    listed = (await client.get("/notes")).json()
    ids = [n["id"] for n in listed]
    assert ids.index(a["id"]) < ids.index(b["id"]), "most-recently-updated should sort first"


@pytest.mark.asyncio
async def test_soft_delete(
    authed_client: tuple[AsyncClient, User], db_session: AsyncSession
) -> None:
    """NOTE-05/D-13: DELETE -> 204, then 404/absent from reads, but the DB row STILL EXISTS with ``deleted_at`` set (soft delete)."""
    client, _user = authed_client
    created = (await client.post("/notes", json={"title": "Doomed"})).json()
    note_id = created["id"]

    deleted = await client.delete(f"/notes/{note_id}")
    assert deleted.status_code == 204

    # Filtered from all reads.
    assert (await client.get(f"/notes/{note_id}")).status_code == 404
    listed_ids = [n["id"] for n in (await client.get("/notes")).json()]
    assert note_id not in listed_ids

    # But the row remains, with deleted_at populated (proves soft delete).
    row = (
        await db_session.execute(select(Page).where(Page.id == uuid.UUID(note_id)))
    ).scalar_one_or_none()
    assert row is not None, "soft delete must NOT remove the row"
    assert row.deleted_at is not None
