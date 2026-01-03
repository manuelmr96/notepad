import datetime
import uuid

from sqlalchemy import ForeignKey, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _default_content() -> dict:
    """Editor-native empty document (CONTEXT.md: persist JSON from day one)."""
    return {"type": "doc", "content": []}


class Page(Base):
    """The LOCKED forward-compatible note/page schema.

    Designed ONCE with every column it needs through Phase 5 so later phases
    extend additively rather than reshape (STATE.md locked decision):
      - ``parent_id`` is DORMANT until Phase 4 (self-referential nesting).
      - ``content`` holds editor-native JSON (Phase 2 markdown / Phase 5 blocks
        are content-format upgrades gated by ``content_schema_version``, never
        schema migrations).
      - ``sort_key`` is reserved for Phase 4 sibling ordering.
      - ``deleted_at`` powers soft-delete (D-13).
    """

    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Dormant until Phase 4 — present now so nesting is an additive feature, not a migration.
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pages.id", ondelete="CASCADE"),
        index=True,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(default="", server_default="")  # D-06
    content: Mapped[dict] = mapped_column(JSONB, default=_default_content)
    content_schema_version: Mapped[int] = mapped_column(default=1, server_default=text("1"))
    sort_key: Mapped[str] = mapped_column(default="", server_default="")  # reserved Phase 4
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=text("now()"))
    updated_at: Mapped[datetime.datetime] = mapped_column(
        server_default=text("now()"),
        onupdate=func.now(),  # bump on edit -> drives most-recently-updated sort
    )
    # Soft delete (D-13): all queries filter ``deleted_at IS NULL``.
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True, index=True)
