"""AUTH-01..05 integration tests for the /auth surface.

These run against the Wave-0 ``app_client`` fixture (httpx AsyncClient over
ASGITransport with the transactional test-session override). They require a
reachable Postgres; on a host without one they still *collect* cleanly and are
executed for real under ``docker compose exec backend pytest`` in Plan 08.

Coverage:
  * register + auto-login + refresh cookie       (AUTH-01, D-10)
  * duplicate registration -> 409
  * login with valid creds                        (AUTH-02)
  * login anti-enumeration: identical generic 401 (AUTH-02, T-04-02)
  * refresh rotation                              (AUTH-03, T-04-03)
  * logout revokes the refresh token              (AUTH-04)
  * logout-all forced revocation                  (AUTH-05)
  * refresh cookie carries HttpOnly/SameSite=Strict and a Path that the BROWSER
    will actually send on the public /api/auth/refresh boot path (T-04-04/05,
    AUTH-03 reload regression)
"""

import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _insecure_cookies(monkeypatch):
    """Force ``COOKIE_SECURE=False`` for the duration of each test.

    The test client talks plain ``http://test`` (ASGITransport), so a ``Secure``
    cookie would be dropped by httpx's cookie jar and the refresh-flow assertions
    would fail purely due to the transport — independent of app correctness. We
    still assert the security attributes (HttpOnly / SameSite=Strict / Path) via
    the raw Set-Cookie header in ``test_refresh_cookie_attributes``.
    """
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)


def _unique_email() -> str:
    # Use example.com (a non-reserved, EmailStr-valid domain). The .local TLD is
    # rejected by email-validator as a special-use name, and these requests go
    # through the UserCreate(EmailStr) schema.
    return f"auth-{uuid.uuid4().hex[:10]}@example.com"


def _set_cookie_header(response) -> str:
    """Return the raw Set-Cookie header for the refresh token (or "")."""
    for key, value in response.headers.multi_items():
        if key.lower() == "set-cookie" and value.startswith("refresh_token="):
            return value
    return ""


async def _register(client: AsyncClient, email: str, password: str = "password123"):
    return await client.post("/auth/register", json={"email": email, "password": password})


# --------------------------------------------------------------------------- #
# AUTH-01 / D-10: register auto-logs-in and sets a refresh cookie
# --------------------------------------------------------------------------- #
async def test_register(app_client: AsyncClient):
    email = _unique_email()
    resp = await _register(app_client, email)

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["access_token"]  # auto-login: access token returned in body
    assert body["token_type"] == "bearer"
    assert "refresh_token" in resp.cookies  # refresh cookie set


async def test_register_duplicate(app_client: AsyncClient):
    email = _unique_email()
    first = await _register(app_client, email)
    assert first.status_code == 201, first.text

    second = await _register(app_client, email)
    assert second.status_code == 409, second.text


# --------------------------------------------------------------------------- #
# AUTH-02: login + anti-enumeration generic error
# --------------------------------------------------------------------------- #
async def test_login(app_client: AsyncClient):
    email = _unique_email()
    await _register(app_client, email, "password123")

    resp = await app_client.post("/auth/login", json={"email": email, "password": "password123"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]
    assert "refresh_token" in resp.cookies


async def test_login_bad(app_client: AsyncClient):
    email = _unique_email()
    await _register(app_client, email, "password123")

    # Wrong password for an existing user.
    bad_pw = await app_client.post(
        "/auth/login", json={"email": email, "password": "wrong-password"}
    )
    # Unknown email entirely.
    unknown = await app_client.post(
        "/auth/login",
        json={"email": _unique_email(), "password": "password123"},
    )

    assert bad_pw.status_code == 401
    assert unknown.status_code == 401
    # Identical generic message => no user enumeration (T-04-02).
    assert bad_pw.json()["detail"] == "Incorrect email or password."
    assert unknown.json()["detail"] == "Incorrect email or password."
    assert bad_pw.json()["detail"] == unknown.json()["detail"]


# --------------------------------------------------------------------------- #
# AUTH-03: silent refresh with rotation
# --------------------------------------------------------------------------- #
async def test_refresh(app_client: AsyncClient):
    email = _unique_email()
    reg = await _register(app_client, email)
    old_cookie = reg.cookies["refresh_token"]

    # The cookie is now scoped to COOKIE_PATH (/api/auth), so httpx's jar would
    # NOT send the auto-stored register cookie on the direct /auth/refresh request
    # this harness uses (it strips the /api proxy prefix). Re-seed at path="/" so
    # the cookie rides along — a transport detail; the cookie *scope* the browser
    # relies on is asserted in test_refresh_cookie_path_covers_public_refresh_path.
    app_client.cookies.set("refresh_token", old_cookie, path="/")
    resp = await app_client.post("/auth/refresh")
    assert resp.status_code == 200, resp.text
    assert resp.json()["access_token"]
    new_cookie = resp.cookies["refresh_token"]

    # Rotation: a brand-new refresh value is issued.
    assert new_cookie != old_cookie

    # The OLD refresh token no longer works (it was revoked on rotation).
    # Re-seed at path="/" so httpx sends it on the direct /auth/refresh request
    # regardless of the app's configured COOKIE_PATH (transport detail only).
    app_client.cookies.set("refresh_token", old_cookie, path="/")
    replay = await app_client.post("/auth/refresh")
    assert replay.status_code == 401


def _cookie_path(set_cookie_header: str) -> str:
    """Extract the Path= attribute value from a raw Set-Cookie header (or "")."""
    for attr in set_cookie_header.split(";"):
        name, _, value = attr.strip().partition("=")
        if name.lower() == "path":
            return value
    return ""


async def test_refresh_cookie_attributes(app_client: AsyncClient):
    """The refresh cookie must be HttpOnly + SameSite=Strict (T-04-04/05)."""
    email = _unique_email()
    reg = await _register(app_client, email)
    header = _set_cookie_header(reg)

    assert header, "no refresh_token Set-Cookie header found"
    lowered = header.lower()
    assert "httponly" in lowered
    assert "samesite=strict" in lowered


async def test_refresh_cookie_path_covers_public_refresh_path(app_client: AsyncClient):
    """REGRESSION (AUTH-03 reload logout): the refresh cookie's Path MUST be a
    prefix of the public, browser-visible refresh path.

    The browser reaches the API same-origin through the `/api` proxy mount (Vite
    dev proxy + nginx), so on app boot ``bootstrapAuth()`` issues
    ``POST /api/auth/refresh``. Per RFC 6265 path-matching, the browser only sends
    the cookie when the request path is *under* the cookie's Path. A cookie scoped
    to the bare ``/auth`` therefore is NEVER sent on ``/api/auth/refresh`` and the
    user gets logged out on every reload.

    Why the other refresh tests don't catch this: ``app_client`` (httpx
    ASGITransport) hits the app directly at ``/auth/refresh`` with no ``/api``
    prefix, so httpx's cookie jar matches ``Path=/auth`` against ``/auth/refresh``
    and the cookie rides along — the harness never exercises the ``/api`` mount the
    browser actually uses. This test asserts the *scope* instead of the transport.
    """
    public_refresh_path = "/api/auth/refresh"

    # Configured scope must itself be a path-boundary prefix of the public path.
    assert public_refresh_path.startswith(settings.COOKIE_PATH)
    boundary = public_refresh_path[len(settings.COOKIE_PATH) :]
    assert boundary == "" or boundary.startswith("/"), (
        f"COOKIE_PATH {settings.COOKIE_PATH!r} is not a clean path prefix of "
        f"{public_refresh_path!r}"
    )

    # And the actual Set-Cookie header on register must use that scope. This is
    # what fails loudly if someone reverts path back to "/auth".
    reg = await _register(app_client, _unique_email())
    cookie_path = _cookie_path(_set_cookie_header(reg))
    assert cookie_path == settings.COOKIE_PATH, (
        f"refresh cookie Path={cookie_path!r} will not be sent by the browser on "
        f"{public_refresh_path!r}"
    )
    # Explicit guard against the regressed value.
    assert cookie_path != "/auth"
    assert public_refresh_path.startswith(cookie_path)


# --------------------------------------------------------------------------- #
# AUTH-04 / AUTH-05: logout + logout-all revoke via the denylist
# --------------------------------------------------------------------------- #
async def test_logout_revokes(app_client: AsyncClient):
    email = _unique_email()
    reg = await _register(app_client, email)
    token = reg.json()["access_token"]
    cookie = reg.cookies["refresh_token"]

    # Re-seed at path="/" so httpx sends the cookie on the direct /auth/logout
    # request (the register cookie is scoped to COOKIE_PATH=/api/auth, which this
    # direct-to-app harness does not path-match). Logout must SEE the cookie to
    # revoke it.
    app_client.cookies.set("refresh_token", cookie, path="/")
    logout = await app_client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 204, logout.text

    # The revoked refresh token must no longer mint access tokens.
    app_client.cookies.set("refresh_token", cookie, path="/")
    after = await app_client.post("/auth/refresh")
    assert after.status_code == 401


async def test_logout_all_revokes(app_client: AsyncClient):
    email = _unique_email()
    # Session 1.
    reg1 = await _register(app_client, email)
    token = reg1.json()["access_token"]
    cookie1 = reg1.cookies["refresh_token"]
    # Session 2 (login again => second active refresh token for same user).
    login2 = await app_client.post("/auth/login", json={"email": email, "password": "password123"})
    cookie2 = login2.cookies["refresh_token"]

    revoke = await app_client.post("/auth/logout-all", headers={"Authorization": f"Bearer {token}"})
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["revoked"] >= 2  # AUTH-05 forced revocation of all sessions

    # Both sessions' refresh tokens are now dead.
    for cookie in (cookie1, cookie2):
        app_client.cookies.set("refresh_token", cookie, path="/")
        resp = await app_client.post("/auth/refresh")
        assert resp.status_code == 401
