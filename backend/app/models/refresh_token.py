import datetime
import uuid

from sqlalchemy import ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RefreshToken(Base):
    """Refresh-token denylist row for forced revocation (AUTH-05); stores only the token HASH, never the raw token (T-03-02)."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(nullable=False)
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=text("now()"))
