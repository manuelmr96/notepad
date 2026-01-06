"""Repository layer: encapsulates all DB access behind typed methods.

Routers depend on these repositories rather than touching the session/ORM
directly, keeping query logic (and per-user scoping) in one place.
"""

from app.repositories.note import NoteRepository
from app.repositories.refresh_token import RefreshTokenRepository
from app.repositories.user import UserRepository

__all__ = ["UserRepository", "RefreshTokenRepository", "NoteRepository"]
