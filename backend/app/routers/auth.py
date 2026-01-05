"""Email/password auth surface (AUTH-01..05).

Token model (per CLAUDE.md / 01-RESEARCH Pattern 4):
  * Access token: short-lived JWT (~15 min), returned in the JSON body only and
    held in client memory — never in a cookie (T-04-04).
  * Refresh token: high-entropy random value in an httpOnly / Secure /
    SameSite=Strict cookie scoped to ``/auth``. Only its sha256 hash is stored in
    the Postgres ``refresh_tokens`` denylist (T-04-07); validity is the denylist,
    not the cookie alone.

Security controls:
  * /login is rate-limited (slowapi, T-04-01) and returns an identical generic
    401 for both bad-password and unknown-email, with dummy-hash timing
    equalization (T-04-02).
  * /refresh ROTATES: the presented token is revoked and a new one issued; a
    revoked/replayed token returns 401 (T-04-03). Reuse-detection family-revoke
    is a documented stretch (Open Question 2).
  * /logout revokes the current refresh token; /logout-all revokes every active
    session for the user (AUTH-05 forced revocation).
"""

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

# A fixed, valid Argon2 hash used to equalize verify timing when the looked-up
# user does not exist, so unknown-email and bad-password cost the same (T-04-02).
_DUMMY_HASH = hash_password("dummy-password-for-timing-equalization")


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        "refresh_token",
        raw,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        path="/auth",
        max_age=settings.REFRESH_TOKEN_TTL_DAYS * 86400,
    )


async def _issue_tokens(
    response: Response, user: User, rt_repo: RefreshTokenRepository
) -> TokenResponse:
    """Mint an access token + a fresh refresh token, persisting only its hash."""
    access_token = make_access_token(str(user.id))
    raw = new_refresh_token()
    expires_at = datetime.datetime.now(datetime.UTC) + datetime.timedelta(
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
    # Always run a hash verify (against the real or a dummy hash) so missing-user
    # and bad-password take equal time (anti-enumeration, T-04-02).
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
        response.delete_cookie("refresh_token", path="/auth")
        raise unauthorized

    # Rotate: revoke the presented token, issue a brand-new one (T-04-03).
    await rt_repo.revoke(old_hash)
    user = await UserRepository(session).get_by_id(token.user_id)
    if user is None:
        response.delete_cookie("refresh_token", path="/auth")
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
    response.delete_cookie("refresh_token", path="/auth")
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
    response.delete_cookie("refresh_token", path="/auth")
    return {"revoked": revoked}
