"""Refresh-token denylist ops (rotation + per-token + forced revocation): only HASHES are stored/compared (T-04-07); a token is active iff it exists, is unrevoked, and unexpired."""

import datetime
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


def _now() -> datetime.datetime:
    # NAIVE UTC: expires_at/revoked_at are TIMESTAMP WITHOUT TIME ZONE; asyncpg rejects tz-aware values for naive columns.
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime.datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(token)
        await self.session.flush()
        return token

    async def get_active_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > _now(),
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, token_hash: str) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=_now())
        )
        await self.session.flush()

    async def revoke_all(self, user_id: uuid.UUID) -> int:
        """Forced revocation of every active session for a user (AUTH-05); returns the count revoked."""
        result = await self.session.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None),
            )
            .values(revoked_at=_now())
        )
        await self.session.flush()
        return result.rowcount
