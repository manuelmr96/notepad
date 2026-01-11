from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """12-factor settings read from the environment; DATABASE_URL and SECRET_KEY required, no hardcoded secrets."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str  # postgresql+asyncpg://...
    SECRET_KEY: str
    ACCESS_TOKEN_TTL_MINUTES: int = 15
    REFRESH_TOKEN_TTL_DAYS: int = 30
    CORS_ORIGINS: str = ""  # comma-separated; empty => same-origin, no CORS
    COOKIE_SECURE: bool = True
    # Refresh-cookie path scope; MUST prefix the public /api/auth/refresh path (RFC 6265), not bare /auth.
    COOKIE_PATH: str = "/api/auth"


settings = Settings()  # type: ignore[call-arg]
