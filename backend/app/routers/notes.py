"""Per-user-isolated note CRUD API (NOTE-01..05 + SEC-01): every handler is behind ``get_current_user`` and owner-scopes via the repository; missing/cross-user => 404 not 403 (T-05-02); delete is soft (D-13)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.deps import get_current_user
from app.models import User
from app.repositories import NoteRepository
from app.schemas import NoteCreate, NoteRead, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])

# 404 (not 403) on missing/cross-user note so existence is never leaked (T-05-02).
_NOT_FOUND = HTTPException(404, detail="Note not found")


@router.get("", response_model=list[NoteRead])
async def list_notes(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NoteRead]:
    """List the caller's non-deleted notes, most-recently-updated first (NOTE-02)."""
    repo = NoteRepository(session)
    notes = await repo.list(current_user.id)
    return [NoteRead.model_validate(n) for n in notes]


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NoteRead:
    """Create a note owned by the caller (NOTE-01; frictionless instant-create D-05)."""
    repo = NoteRepository(session)
    note = await repo.create(current_user.id, body)
    return NoteRead.model_validate(note)


@router.get("/{note_id}", response_model=NoteRead)
async def get_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NoteRead:
    """Open one of the caller's notes (NOTE-03). 404 if missing/cross-user (SEC-01)."""
    repo = NoteRepository(session)
    note = await repo.get(current_user.id, note_id)
    if not note:
        raise _NOT_FOUND
    return NoteRead.model_validate(note)


@router.patch("/{note_id}", response_model=NoteRead)
async def update_note(
    note_id: uuid.UUID,
    body: NoteUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NoteRead:
    """Partial-update a note (NOTE-04, idempotent autosave). 404 if missing/cross-user."""
    repo = NoteRepository(session)
    note = await repo.update(current_user.id, note_id, body)
    if not note:
        raise _NOT_FOUND
    return NoteRead.model_validate(note)


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Soft-delete a note (NOTE-05, D-13). 404 if missing/cross-user (SEC-01)."""
    repo = NoteRepository(session)
    ok = await repo.soft_delete(current_user.id, note_id)
    if not ok:
        raise _NOT_FOUND
