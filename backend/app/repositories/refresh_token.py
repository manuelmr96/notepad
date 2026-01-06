"""Refresh-token denylist operations (rotation + per-token + forced revocation).

Only token HASHES are ever stored or compared (T-04-07); the raw token lives
solely in the client's httpOnly cookie. A token is "active" iff it exists, has
not been revoked, and has not expired — this is the source of truth for refresh
validity, not the cookie alone (the cookie↔denylist trust boundary).
"""

import datetime
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RefreshToken


def _now() -> datetime.datetime:
    # NAIVE UTC: the refresh_tokens.expires_at / revoked_at columns are
    # TIMESTAMP WITHOUT TIME ZONE (Plan 03 locked schema, matching `now()`
    # server defaults). asyncpg refuses to bind a tz-aware datetime to a naive
    # column, so all comparisons/writes here use naive UTC.
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
        """Forced revocation of every active session for a user (AUTH-05).

        Returns the number of tokens revoked.
        """
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
