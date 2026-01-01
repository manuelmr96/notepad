import datetime

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
