from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """12-factor application settings, read entirely from the environment.

    No secrets are hardcoded here. `DATABASE_URL` and `SECRET_KEY` are required
    and must be supplied via env vars (or a gitignored local `.env`).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str  # postgresql+asyncpg://...
    SECRET_KEY: str
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30
    CORS_ORIGINS: str = ""  # comma-separated; empty => same-origin, no CORS
    COOKIE_SECURE: bool = True
    # Path scope for the refresh-token cookie. MUST be a prefix of the public,
    # browser-visible refresh path. The SPA reaches the API same-origin under the
    # `/api` proxy mount (Vite dev proxy + nginx `location /api/`), so the browser
    # issues `POST /api/auth/refresh`. Per RFC 6265 path-matching, the cookie is
    # only sent on request paths under this value — it MUST cover `/api/auth/...`,
    # not the bare `/auth` (which the browser never requests directly).
    COOKIE_PATH: str = "/api/auth"


settings = Settings()  # type: ignore[call-arg]
