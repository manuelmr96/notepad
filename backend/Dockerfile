# syntax=docker/dockerfile:1

# ---- Build stage: resolve deps into a venv with uv ----
FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy only dependency manifests first for layer caching.
COPY pyproject.toml uv.lock ./

# Install runtime dependencies (no dev group) into /app/.venv from the locked set.
RUN uv sync --frozen --no-dev --no-install-project

# ---- Runtime stage: slim image with the prebuilt venv + app source ----
FROM python:3.13-slim

WORKDIR /app

# Bring the resolved virtualenv from the build stage.
COPY --from=build /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy application source plus the Alembic config + migrations, which the
# Compose start command runs via `alembic upgrade head` (migrate-on-start).
COPY app ./app
COPY pyproject.toml ./
COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8000

# Plan 08's Compose file overrides CMD to prepend `alembic upgrade head`.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
