"""Shared FastAPI dependencies.

``get_current_user`` decodes and validates the Bearer access token (signature,
expiry, and ``type == "access"``) and resolves it to a ``User`` row. It is the
single auth gate consumed by every protected route (e.g. the notes router in
Plan 05). All failure modes return a generic 401 so an attacker cannot
distinguish "no token" / "bad token" / "unknown user" (T-04-06).
"""

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import decode_access_token
from app.models import User
from app.repositories import UserRepository

# auto_error=False so we can return our own generic 401 (rather than FastAPI's
# default 403) when no credentials are supplied.
_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise invalid from exc

    if payload.get("type") != "access":
        raise invalid

    sub = payload.get("sub")
    if not sub:
        raise invalid
    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError) as exc:
        raise invalid from exc

    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise invalid
    return user
