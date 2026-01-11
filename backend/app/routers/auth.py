"""Email/password auth surface (AUTH-01..05): in-memory access JWT + httpOnly/Secure/SameSite=Strict refresh cookie (only its hash stored, T-04-07), rate-limited anti-enumeration /login (T-04-01/02), rotating /refresh (T-04-03), and /logout[-all] revocation (AUTH-05)."""

import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.deps import get_current_user
from app.core.security import (
    hash_password,
    hash_refresh_token,
    make_access_token,
    new_refresh_token,
    verify_password,
)
from app.models import User
from app.repositories import RefreshTokenRepository, UserRepository
from app.schemas import TokenResponse, UserCreate
from app.state import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

# Fixed valid Argon2 hash to equalize verify timing for unknown users so unknown-email and bad-password cost the same (T-04-02).
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        "refresh_token",
        raw,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        path=settings.COOKIE_PATH,
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 86400,
    )


async def _issue_tokens(
    response: Response, user: User, rt_repo: RefreshTokenRepository
) -> TokenResponse:
    """Mint an access token + a fresh refresh token, persisting only its hash."""
    access_token = make_access_token(str(user.id))
    raw = new_refresh_token()
    # Naive UTC to match the TIMESTAMP WITHOUT TIME ZONE expires_at column; asyncpg rejects tz-aware values for naive columns.
    expires_at = datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(
        days=settings.REFRESH_TOKEN_TTL_DAYS
    )
    await rt_repo.create(user.id, hash_refresh_token(raw), expires_at)
    _set_refresh_cookie(response, raw)
    return TokenResponse(access_token=access_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    users = UserRepository(session)
    if await users.get_by_email(payload.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = await users.create(payload.email, hash_password(payload.password))
    tokens = await _issue_tokens(response, user, RefreshTokenRepository(session))
    await session.commit()
    return tokens


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: UserCreate,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    users = UserRepository(session)
    user = await users.get_by_email(payload.email)
    # Always run a hash verify (real or dummy hash) so missing-user and bad-password take equal time (anti-enumeration, T-04-02).
    target_hash = user.hashed_password if user is not None else _DUMMY_HASH
    valid = verify_password(payload.password, target_hash)
    if user is None or not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    tokens = await _issue_tokens(response, user, RefreshTokenRepository(session))
    await session.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> TokenResponse:
    raw = request.cookies.get("refresh_token")
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
    )
    if not raw:
        raise unauthorized

    rt_repo = RefreshTokenRepository(session)
    old_hash = hash_refresh_token(raw)
    token = await rt_repo.get_active_by_hash(old_hash)
    if token is None:
        # Unknown / revoked / expired -> clear the stale cookie and reject.
        response.delete_cookie("refresh_token", path=settings.COOKIE_PATH)
        raise unauthorized

    # Rotate: revoke the presented token, issue a brand-new one (T-04-03).
    await rt_repo.revoke(old_hash)
    user = await UserRepository(session).get_by_id(token.user_id)
    if user is None:
        response.delete_cookie("refresh_token", path=settings.COOKIE_PATH)
        raise unauthorized
    tokens = await _issue_tokens(response, user, rt_repo)
    await session.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    raw = request.cookies.get("refresh_token")
    if raw:
        await RefreshTokenRepository(session).revoke(hash_refresh_token(raw))
        await session.commit()
    response.delete_cookie("refresh_token", path=settings.COOKIE_PATH)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout-all")
async def logout_all(
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    revoked = await RefreshTokenRepository(session).revoke_all(user.id)
    await session.commit()
    response.delete_cookie("refresh_token", path=settings.COOKIE_PATH)
    return {"revoked": revoked}
