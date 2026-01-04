import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


def _default_content() -> dict:
    return {"type": "doc", "content": []}


class NoteCreate(BaseModel):
    """Create payload (NOTE-01). Instant-create (D-05): both fields optional."""

    title: str = ""
    content: dict = Field(default_factory=_default_content)


class NoteRead(BaseModel):
    """Note representation returned to the client."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    content: dict
    content_schema_version: int
    created_at: datetime.datetime
    updated_at: datetime.datetime


class NoteUpdate(BaseModel):
    """Partial update (NOTE-04). All fields optional => idempotent PATCH for autosave.

    Use ``model_dump(exclude_unset=True)`` so an empty patch is a no-op.
    """

    title: str | None = None
    content: dict | None = None
