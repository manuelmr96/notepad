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
    """Partial update (NOTE-04); all fields optional => idempotent autosave PATCH (empty patch is a no-op via exclude_unset)."""

    title: str | None = None
    content: dict | None = None
