"""Per-user-isolated note (Page) persistence — the SEC-01 boundary: every method scopes by ``owner_id`` + ``deleted_at IS NULL`` (T-05-01/02), and delete is soft (D-13)."""

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
        # MUST commit (not just flush): the per-request session never commits after yield, so a flush-only create is rolled back and the row never persists.
        await self.session.commit()
        await self.session.refresh(page)
        return page

    async def update(self, user_id: uuid.UUID, note_id: uuid.UUID, data: NoteUpdate) -> Page | None:
        """Partial, idempotent autosave update (NOTE-04/06): applies only set fields, owner-scoped (missing/cross-user => None => 404), updated_at auto-bumps."""
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
        """Soft-delete an owned note (D-13): set ``deleted_at``; returns True iff one owned, not-already-deleted row matched (cross-user touches nothing, T-05-01)."""
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
