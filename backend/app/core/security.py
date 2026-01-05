import datetime
import hashlib
import secrets

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

# Argon2id with sane recommended parameters (pwdlib successor to passlib).
_pwd = PasswordHash.recommended()


def hash_password(p: str) -> str:
    return _pwd.hash(p)


def verify_password(p: str, h: str) -> bool:
    return _pwd.verify(p, h)


def make_access_token(sub: str) -> str:
    now = datetime.datetime.now(datetime.UTC)
    exp = now + datetime.timedelta(minutes=settings.ACCESS_TOKEN_TTL_MINUTES)
    return jwt.encode(
        {"sub": sub, "exp": exp, "iat": now, "type": "access"},
        settings.SECRET_KEY,
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])


def new_refresh_token() -> str:
    """Generate a fresh, high-entropy raw refresh token.

    The raw value is returned ONLY to be set in the httpOnly cookie; it is never
    persisted. The server stores ``hash_refresh_token(raw)`` instead (T-04-07).
    """
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw: str) -> str:
    """Hash a raw refresh token for storage/lookup (sha256 -> 64 hex chars).

    SHA-256 (not Argon2) is intentional: the token is already high-entropy random,
    so a fast deterministic hash gives constant-time-friendly equality lookups in
    the denylist without the cost of a password KDF.
    """
    return hashlib.sha256(raw.encode()).hexdigest()
