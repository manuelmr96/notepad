from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Single declarative base shared by ORM models and Alembic metadata."""


# `pool_pre_ping` recycles dead connections; async engine + asyncpg keeps the API non-blocking/stateless.
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

# `expire_on_commit=False` prevents post-commit lazy reloads (avoids MissingGreenlet when serializing ORM objects).
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a per-request AsyncSession."""
    async with SessionLocal() as session:
        yield session
