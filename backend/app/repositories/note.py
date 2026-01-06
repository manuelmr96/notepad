"""Per-user-isolated note (Page) persistence — the SEC-01 security boundary.

The isolation guarantee lives HERE, not in the router or UI: EVERY method takes
``user_id`` and includes ``Page.owner_id == user_id`` (plus
``Page.deleted_at IS NULL``) in its WHERE clause. There is intentionally no
method that touches a page without scoping by owner — an attacker-controlled
``note_id`` can never reach another user's row (T-05-01). The router translates a
``None``/``False`` miss into a 404 (never 403) so existence is not leaked
(T-05-02).

Delete is SOFT (D-13 / T-05-05): ``deleted_at`` is set and every query filters
``deleted_at IS NULL`` — the row remains for Phase 2 trash/restore.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Page
from app.schemas import NoteCreate, NoteUpdate


class NoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, user_id: uuid.UUID) -> Sequence[Page]:
        """Owner's non-deleted notes, most-recently-updated first (CONTEXT.md)."""
        result = await self.session.execute(
            select(Page)
            .where(Page.owner_id == user_id, Page.deleted_at.is_(None))
            .order_by(Page.updated_at.desc())
        )
        return result.scalars().all()

    async def get(self, user_id: uuid.UUID, note_id: uuid.UUID) -> Page | None:
        """Fetch a single owned, non-deleted note (None => router 404)."""
        result = await self.session.execute(
            select(Page).where(
                Page.id == note_id,
                Page.owner_id == user_id,
                Page.deleted_at.is_(None),
            )
        )
        return result.scalars().first()

    async def create(self, user_id: uuid.UUID, data: NoteCreate) -> Page:
        """Insert a new note owned by ``user_id`` (NOTE-01)."""
        page = Page(
            owner_id=user_id,
            title=data.title,
            content=data.content,
            content_schema_version=1,
        )
        self.session.add(page)
        await self.session.flush()
        await self.session.refresh(page)
        return page

    async def update(self, user_id: uuid.UUID, note_id: uuid.UUID, data: NoteUpdate) -> Page | None:
        """Partial, idempotent update for autosave (NOTE-04/06).

        Only fields explicitly set on the payload are applied
        (``model_dump(exclude_unset=True)``), so an empty PATCH is a no-op. The
        target row is fetched via ``get`` (owner-scoped), so a missing/cross-user
        note returns ``None`` => router 404. ``updated_at`` auto-bumps via the
        model's ``onupdate`` (Plan 03)."""
        result = await self.session.execute(
            select(Page).where(
                Page.id == note_id,
                Page.owner_id == user_id,
                Page.deleted_at.is_(None),
            )
        )
        page = result.scalars().first()
        if page is None:
            return None
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(page, field, value)
        await self.session.commit()
        await self.session.refresh(page)
        return page

    async def soft_delete(self, user_id: uuid.UUID, note_id: uuid.UUID) -> bool:
        """Soft-delete an owned note (D-13): set ``deleted_at`` (row remains).

        Returns ``True`` iff exactly one owned, not-already-deleted row matched
        (``False`` => router 404). The owner filter is in the WHERE clause so a
        cross-user delete touches nothing (T-05-01)."""
        result = await self.session.execute(
            update(Page)
            .where(
                Page.id == note_id,
                Page.owner_id == user_id,
                Page.deleted_at.is_(None),
            )
            .values(deleted_at=func.now())
        )
        await self.session.commit()
        return result.rowcount == 1
