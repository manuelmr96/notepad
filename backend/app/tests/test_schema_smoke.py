"""Schema smoke test: proves the ORM + test harness work before auth/notes land.

Inserts a User + a Page, reads the Page back, and asserts the locked defaults
(``content`` empty doc JSON, ``content_schema_version == 1``). Requires a
reachable Postgres; under ``docker compose exec backend pytest`` (Plan 08) or a
local test DB it runs for real. ``pytest --collect-only`` succeeds without a DB.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Page, User


async def test_page_defaults_persist(db_session: AsyncSession) -> None:
    user = User(
        email=f"smoke-{uuid.uuid4().hex[:8]}@test.local",
        hashed_password="x",  # not exercised here; hashing covered by auth tests
    )
    db_session.add(user)
    await db_session.flush()

    page = Page(owner_id=user.id, title="hello")
    db_session.add(page)
    await db_session.flush()

    fetched = (await db_session.scalars(select(Page).where(Page.id == page.id))).one()

    assert fetched.owner_id == user.id
    assert fetched.title == "hello"
    # Locked editor-native default document + schema version (CONTEXT.md / D-06).
    assert fetched.content == {"type": "doc", "content": []}
    assert fetched.content_schema_version == 1
    # Forward-compatible columns exist and default sanely.
    assert fetched.parent_id is None
    assert fetched.deleted_at is None
    assert fetched.sort_key == ""
