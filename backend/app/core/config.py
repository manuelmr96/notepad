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


settings = Settings()  # type: ignore[call-arg]
