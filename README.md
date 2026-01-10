# Notepad

A self-hostable, containerized note-taking web app: a React (Vite + TypeScript)
SPA talking to a FastAPI (Python) backend over a same-origin `/api` reverse
proxy, with PostgreSQL for storage. It starts as a multi-user notes app and is
designed to grow, phase by phase, into a Notion-like workspace.

**Core value:** a logged-in user can reliably create, edit, and find their own
notes.

## Architecture

```
                        docker compose network
  ┌──────────┐ :5173   ┌──────────────────────┐   /api   ┌─────────────┐
  │ browser  │ ──────▶ │ frontend (nginx)      │ ───────▶ │ backend     │
  │          │         │  static SPA + proxy   │          │ (FastAPI)   │
  └──────────┘         └──────────────────────┘          └──────┬──────┘
                                                                 │ asyncpg
                                                          ┌──────▼──────┐
                                                          │ postgres 17 │
                                                          │  (pgdata)   │
                                                          └─────────────┘
```

- **Same-origin:** nginx serves the built SPA and reverse-proxies `/api` to the
  backend, so the refresh cookie stays `SameSite=Strict` with no CORS config.
- **Stateless backend:** any backend instance validates JWTs and reaches the DB;
  the only stateful piece is the `pgdata` named volume.
- **Migrate-on-start:** the backend runs `alembic upgrade head` before serving,
  gated by the Postgres healthcheck — no hand-applied schema, no startup race.

## Prerequisites

- Docker and Docker Compose v2 (`docker compose version`)

## Quickstart

```sh
# 1. Create your env file and set a strong SECRET_KEY.
cp .env.example .env
# Generate a key and paste it into .env as SECRET_KEY:
openssl rand -hex 32

# 2. Build and start the full stack (postgres + backend + frontend).
docker compose up --build
```

Then open:

- App: <http://localhost:5173>
- API docs (Swagger): <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

On first boot the backend waits for Postgres to become healthy, applies the
Alembic migration (`alembic upgrade head`) to create the schema, then starts
serving. Register an account in the app and start taking notes.

Stop the stack with `Ctrl-C`, or in another terminal:

```sh
docker compose down        # stop containers, keep the database volume
docker compose down -v     # also delete pgdata (full reset)
```

For a foreground/background bring-up: `docker compose up --build -d`.

## Configuration

All configuration is read from the environment (12-factor). See
[`.env.example`](.env.example) for the full, documented set:

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Async SQLAlchemy/asyncpg connection string |
| `SECRET_KEY` | JWT signing key (`openssl rand -hex 32`) |
| `ACCESS_TOKEN_TTL_MINUTES` | Access-token lifetime (default 15) |
| `REFRESH_TOKEN_TTL_DAYS` | Refresh-token lifetime (default 30) |
| `CORS_ORIGINS` | Comma-separated origins; empty = same-origin (default) |
| `COOKIE_SECURE` | Refresh-cookie `Secure` flag — `false` for local HTTP dev, **`true` in production (HTTPS)** |

## Running tests

With the stack running (`docker compose up -d`):

**Backend** (auth, notes CRUD, and the SEC-01 cross-user isolation test) against
a live Postgres. Use a separate test database so the suite's create/drop schema
harness never touches app data:

```sh
docker compose exec postgres createdb -U notepad notepad_test
docker compose exec -e TEST_DATABASE_URL=postgresql+asyncpg://notepad:notepad@postgres:5432/notepad_test \
  backend pytest -q
```

**Frontend** (login form + autosave hook):

```sh
cd frontend
npm install
npm run test -- --run
```

## Local development (optional, with HMR)

The Compose `frontend` is the production static build (nginx). For a faster
edit/refresh loop, run the Vite dev server directly while the backend +
Postgres run under Compose:

```sh
docker compose up --build -d postgres backend
cd frontend
npm install
npm run dev          # Vite dev server with an /api proxy to backend:8000
```

The Vite dev proxy mirrors the nginx `/api` reverse proxy, so the same-origin
cookie behaviour is identical to production.

## Project layout

```
backend/    FastAPI app, SQLAlchemy 2.0 models, Alembic migrations, pytest suite
frontend/   Vite + React 19 + TypeScript SPA (Tailwind v4, shadcn/ui)
docker-compose.yml   postgres + backend + frontend orchestration
.env.example         documented environment template
```
