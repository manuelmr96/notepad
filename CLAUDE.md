<!-- GSD:project-start source:PROJECT.md -->
## Project

**Notepad**

A self-hostable, containerized note-taking web app with a React frontend and a Python (FastAPI) backend. It starts as a simple multi-user notes app and grows, phase by phase, into a Notion-like workspace — block-based editing, nested pages, and structured databases/tables. Built for a solo developer who wants a clean, scalable foundation without premature infrastructure.

**Core Value:** A logged-in user can reliably create, edit, and find their own notes — everything else builds on this foundation working flawlessly.

### Constraints

- **Tech stack**: React frontend, FastAPI (Python) backend, PostgreSQL, Docker — fixed by the user up front.
- **Architecture**: Stateless API, containerized, horizontally-scalable-ready — the "scale as much as possible" goal means getting patterns right early, not building heavy infra now.
- **Self-hosting**: Must be fully self-hostable with no required third-party SaaS — user requirement.
- **Cost**: Prefer free/open-source tools and services — cost-sensitive solo project.
- **Team**: Solo developer — keep per-phase complexity manageable.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **React** | 19.2.x | Frontend UI | Fixed constraint. v19 is stable, ships the new compiler-friendly model, Actions, and `use()`. No reason to pin to 18. |
| **Vite** | 7.x (8.0.x available) | Frontend build tool + dev server | **Use Vite, NOT Next.js.** This is an SPA talking to a separate FastAPI backend. Next.js adds an SSR/Node server you don't want (self-hosting cost, two backends, RSC complexity). Vite gives instant HMR, a single static-asset build served by any container/CDN, and zero server runtime. Pin to v7 for max ecosystem compatibility; v8 is fine but newer. |
| **TypeScript** | 5.7+ | Type safety across frontend | Non-negotiable for a project meant to scale. Pairs with typed routing/query for end-to-end safety. |
| **FastAPI** | 0.138.x | Backend API framework | Fixed constraint. Async-native, OpenAPI/Swagger auto-docs, Pydantic v2 integration. |
| **Python** | 3.12 or 3.13 | Backend runtime | 3.12+ for performance + mature async. Use 3.13 only if all C-extension deps (asyncpg, argon2-cffi) have wheels — they do as of 2026-06. |
| **Uvicorn** | 0.49.x | ASGI server | Standard ASGI server for FastAPI. Run behind Gunicorn (`gunicorn -k uvicorn.workers.UvicornWorker`) or with `--workers` in production for multi-process. Stays stateless → K8s-ready. |
| **PostgreSQL** | 17 (16 LTS-safe) | Primary datastore | Fixed constraint. v17 is current GA; v16 is the conservative choice. Both have the JSONB + recursive CTE features the block/nesting model needs. |
### Frontend Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **TanStack Query** (`@tanstack/react-query`) | 5.101.x | Server-state: fetching, caching, invalidation | From Phase 1. This is the single most important frontend choice — it replaces hand-rolled `useEffect` + `useState` data fetching. Handles caching, refetch, optimistic updates (critical for editor UX later). |
| **React Router** (`react-router-dom`) | 7.18.x | Client-side routing | From Phase 1. v7 (the merged Remix/RR) in **SPA/library mode** (`createBrowserRouter`) — do NOT adopt its framework/SSR mode. Mature, ubiquitous, fits nested-page URL structures (`/page/:id`). |
| **Tailwind CSS** | 4.3.x | Styling | From Phase 1. v4 uses the new Oxide engine + CSS-first config (`@theme` in CSS, no large `tailwind.config.js`). Utility-first keeps a solo dev fast; no runtime cost. |
| **shadcn/ui** | latest (copy-in) | Component primitives | From Phase 1. Not an npm dependency — it copies Radix-based, Tailwind-styled components into your repo. Free, MIT, no lock-in, fully self-owned. Gives accessible dialogs/menus/sidebar without a heavyweight UI kit. |
| **Zustand** | 5.0.x | Client (UI) state | When you need cross-component *client* state (sidebar open/closed, editor selection, theme). Keep it minimal — server state lives in TanStack Query, not here. Avoid Redux (overkill for solo project). |
| **Zod** | 4.4.x | Runtime validation / form + API response parsing | From Phase 1. Validate forms and parse API responses into typed objects. Pairs with React Hook Form. |
| **React Hook Form** | 7.x | Form state (login, register, note metadata) | Auth forms in Phase 1; property forms for databases later. Minimal re-renders, integrates with Zod via `@hookform/resolvers`. |
| **Axios** or native `fetch` | — | HTTP client | `fetch` is sufficient; wrap it in a thin client that attaches the auth token and handles 401→refresh. Axios only if you want interceptors out of the box. |
### Backend Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **SQLAlchemy** | 2.0.51 | ORM (async) | **Use SQLAlchemy 2.0 directly, NOT SQLModel** (see rationale below). 2.0's typed `Mapped[]` syntax + `AsyncSession` + `create_async_engine`. The backbone of the data layer. |
| **asyncpg** | 0.31.x | Async PostgreSQL driver | Driver for SQLAlchemy async engine (`postgresql+asyncpg://`). Fastest async Postgres driver. (Alternative: `psycopg` 3.x in async mode — also valid, slightly slower but more featureful.) |
| **Alembic** | 1.18.x | Schema migrations | From Phase 1, before the first table ships. Autogenerate migrations from SQLAlchemy models. Configure for async. Never edit the live schema by hand. |
| **Pydantic** | 2.13.x | Request/response schemas, validation | Core to FastAPI. Define separate `*Create` / `*Read` / `*Update` schemas distinct from ORM models (clean API contract, avoids leaking DB internals). |
| **pydantic-settings** | 2.14.x | 12-factor config from env vars | From Phase 1. Reads `DATABASE_URL`, `SECRET_KEY`, token TTLs from environment — essential for containerized/K8s config and statelessness. |
| **pwdlib[argon2]** | 0.3.x | Password hashing | **Use pwdlib with Argon2id, NOT passlib.** passlib is effectively unmaintained and breaks with modern bcrypt versions; pwdlib is its spiritual successor, recommended by the FastAPI docs, wraps argon2id with sane defaults. |
| **PyJWT** | 2.13.x | JWT encode/decode | **Use PyJWT, NOT python-jose.** python-jose is poorly maintained with open CVEs; PyJWT is the actively maintained standard. Use for short-lived access tokens. |
| **fastapi-users** | 15.0.x | (Optional) batteries-included auth | *Consider* for Phase 1 if you want registration/login/JWT/password-reset out of the box and accept its opinions. **For a learning-oriented solo greenfield, a thin custom auth layer (PyJWT + pwdlib + a `users` table) is recommended** — fewer abstractions, full control, and the scope (email+password+JWT) is small. fastapi-users is the fallback if you'd rather not own that code. |
| **slowapi** | latest | Rate limiting (login endpoint) | Add when auth ships, to throttle brute-force on `/login`. |
### Development Tools
| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Python dependency & venv management | Use `uv` over pip/poetry. Astral's resolver is dramatically faster, produces a lockfile (`uv.lock`), and works cleanly in Docker multi-stage builds. |
| **Ruff** | Python lint + format | Replaces flake8 + isort + black. One fast tool. |
| **mypy** or **Pyright** | Python type checking | Catch type errors before runtime; pairs with SQLAlchemy 2.0 `Mapped[]`. |
| **Biome** or ESLint + Prettier | JS/TS lint + format | Biome is the fast modern single-tool option; ESLint+Prettier is the safe default if you hit plugin gaps. |
| **Vitest** | Frontend unit testing | Vite-native, Jest-compatible API. |
| **pytest** + **pytest-asyncio** + **httpx** | Backend testing | `httpx.AsyncClient` against the FastAPI app for integration tests; pytest-asyncio for async test functions. |
| **Docker + Docker Compose** | Local orchestration | Fixed constraint. Multi-stage Dockerfiles (build → slim runtime). Compose runs frontend, backend, postgres. Keep containers stateless; Postgres data in a named volume. |
## The Block-Editor Decision (drives the data model)
### Why BlockNote / TipTap (ProseMirror family) over Lexical and Plate
| Engine | Foundation | License/Cost | Notion-fit | Verdict for this project |
|--------|-----------|--------------|-----------|--------------------------|
| **BlockNote** | ProseMirror + TipTap | MPL-2.0 core (commercial-OK), GPL-3.0 only for optional "XL" packages — core is free & self-hostable | **Highest** — ships Notion-style block model, slash menu, drag handles, tab-to-nest, and a clean block JSON out of the box | **Recommended.** Biggest head start for a solo dev; you get the Notion UX without building blocks from primitives. |
| **TipTap** | ProseMirror | MIT core (free); only *collaboration cloud/AI* features are paid — irrelevant since realtime is out of scope | High — headless, the de-facto choice for Notion clones | **Recommended fallback** if BlockNote's opinions constrain you or you want full custom block control. |
| **Lexical** | Meta in-house | MIT, fully free | Medium — powerful & performant but lower-level; you build the Notion block UX yourself | Not recommended — more work for a solo dev; its edge (extreme performance, React Native) is irrelevant here. |
| **Plate** | Slate | Free; optional Plate Plus paid | Medium-High — good plugins but Slate has historically had rough edges with complex nesting/normalization | Not recommended — Slate's nested-normalization complexity is a known time sink. |
### How this drives the EARLY data model (decide in Phase 1, before the editor exists)
- `users` — id (UUID), email (unique, citext), hashed_password, created_at.
- `pages` (call them pages, not "notes", from day one) — `id UUID`, `owner_id FK users`, `parent_id UUID NULL FK pages(id)` (self-referential → infinite nesting), `title text`, `position`/`sort_key` for sibling ordering, `created_at`, `updated_at`, and **`content JSONB`** holding the editor document tree.
- The `parent_id` self-reference gives the nested-page hierarchy for free; query the tree with a **recursive CTE** (`WITH RECURSIVE`). Index `parent_id` and `owner_id`.
- Store the editor's document JSON in the `content JSONB` column. In Phase 1 it can be a trivial `{ "type":"doc", "content":[{ "type":"paragraph", ... }] }` (or even plain markdown text in a column) — but choosing JSONB now means Phase 3's block editor is a content-format upgrade, not a schema migration.
## Installation
# --- Frontend (npm) ---
# Core supporting
# Styling (Tailwind v4)
# shadcn/ui added via: npx shadcn@latest init
# Editor (add ~Phase 3)
# OR raw TipTap: npm install @tiptap/react @tiptap/starter-kit @tiptap/pm
# Dev
# --- Backend (uv) ---
# Dev
## Alternatives Considered
| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Vite (SPA) | Next.js / TanStack Start | Only if you later need SSR/SEO for public-shared pages. Not now — adds a Node server, conflicts with the FastAPI-as-sole-backend design. |
| React Router 7 (library mode) | TanStack Router | TanStack Router has superior end-to-end type-safe params/search/loaders. Valid choice if you prioritize that over React Router's larger ecosystem/familiarity. Either is fine; RR7 is the safer default. |
| SQLAlchemy 2.0 | SQLModel | If you strongly prefer one model class shared between DB + API and accept SQLModel's thinner abstraction over a less actively-developed layer. SQLModel (0.0.38, still pre-1.0 after years) lags SQLAlchemy/Pydantic releases and obscures advanced features you'll want for the recursive/relational database feature. SQLAlchemy 2.0 + separate Pydantic schemas is the more robust, future-proof choice. |
| asyncpg | psycopg 3 (async) | psycopg3 if you want LISTEN/NOTIFY, COPY, or a single driver for sync+async. asyncpg is faster for plain query workloads. |
| BlockNote | Raw TipTap | Raw TipTap when BlockNote's block schema is too opinionated or you need deeply custom block types/rendering. More code, more control. |
| pwdlib (Argon2) | bcrypt via pwdlib | bcrypt only if you must interop with an existing bcrypt hash store. Argon2id is the stronger default for greenfield. |
| Custom thin auth | fastapi-users 15 | fastapi-users if you want registration/verification/password-reset/OAuth flows prebuilt and accept its DB-adapter conventions. Good time-saver; less of a learning exercise. |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Next.js** | Pulls in an SSR/RSC Node runtime you don't want with a separate FastAPI backend; doubles deploy surface; SEO/SSR not needed for an auth-gated notes app. | Vite SPA |
| **Create React App** | Deprecated and unmaintained; slow. | Vite |
| **passlib** | Effectively unmaintained; breaks with modern bcrypt; FastAPI docs have moved on. | pwdlib[argon2] |
| **python-jose** | Stale maintenance, known CVEs. | PyJWT |
| **Redux / Redux Toolkit** | Overkill for a solo project; server state belongs in TanStack Query, UI state in Zustand. | TanStack Query + Zustand |
| **Sync SQLAlchemy / Flask-style blocking DB calls** | Blocks the event loop under FastAPI async; kills the "stateless, horizontally scalable" goal. | SQLAlchemy 2.0 async + asyncpg |
| **Storing JWT in localStorage** | XSS-exposed token theft. | httpOnly, Secure, SameSite cookie for the refresh token; access token in memory. |
| **SQLModel for the database feature's complex queries** | Its abstraction makes recursive CTEs / advanced relational joins awkward. | SQLAlchemy 2.0 Core/ORM |
| **CSS-in-JS runtime libs (styled-components/Emotion)** | Runtime cost + React 19/RSC friction; declining ecosystem momentum. | Tailwind CSS v4 |
| **Lexical / Plate** | More low-level work to reach Notion-style blocks; their advantages (perf, RN) don't apply here. | BlockNote / TipTap |
## Stack Patterns by Variant
- Short-lived **access token (JWT, ~15 min)** held in memory on the client.
- Longer-lived **refresh token in an httpOnly Secure SameSite=Strict cookie**; a `/auth/refresh` endpoint mints new access tokens.
- This keeps the API stateless (any pod can validate a JWT) — directly serving the "Kubernetes-ready, horizontally scalable" requirement. Refresh-token revocation list lives in Postgres (or Redis later) only if you need forced logout.
- Add Redis as a fast revocation/denylist + cache. Optional, defer until needed (cost-sensitive).
- BlockNote/TipTap both integrate Yjs CRDTs self-hostable (no SaaS needed) — the editor choice keeps that door open without committing to it now.
## Version Compatibility
| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| React 19.2 | react-router-dom 7, @tanstack/react-query 5 | All support React 19. |
| Tailwind 4.x | Vite 7/8 via `@tailwindcss/vite` | v4 drops the PostCSS-config approach for most setups; use the Vite plugin. |
| SQLAlchemy 2.0.51 | asyncpg 0.31, Pydantic 2.13 | Use `sqlalchemy[asyncio]`; keep ORM models and Pydantic schemas as *separate* classes. |
| FastAPI 0.138 | Pydantic 2.13, Uvicorn 0.49 | FastAPI requires Pydantic v2 (never pin Pydantic v1). |
| Alembic 1.18 | SQLAlchemy 2.0 (async) | Configure `env.py` for async engine (`run_sync` pattern). |
| BlockNote 0.51 | React 18/19, TipTap 3 / ProseMirror | Built on TipTap; bring `@blocknote/mantine` (or shadcn variant) for default UI. |
| pwdlib 0.3 | Python 3.9+ | Install the `[argon2]` extra (pulls argon2-cffi 25.x). |
| Python 3.13 | asyncpg 0.31, argon2-cffi 25 | Wheels available as of 2026-06; 3.12 is the conservative pick. |
## Sources
- npm registry (`npm view`) — verified live versions for vite, react, @tanstack/react-query, react-router-dom, tailwindcss, @tiptap/react, @blocknote/core, lexical, zustand, zod — 2026-06-20 — HIGH
- PyPI JSON API — verified live versions for fastapi, uvicorn, sqlalchemy, sqlmodel, alembic, pydantic, pydantic-settings, asyncpg, psycopg, fastapi-users, pwdlib, pyjwt, argon2-cffi — 2026-06-20 — HIGH
- Context7 `/fastapi/fastapi`, `/vitejs/vite` — version + best-practice confirmation — HIGH
- TestDriven.io "FastAPI with Async SQLAlchemy, SQLModel, and Alembic" — async DB patterns — MEDIUM
- BuildPilot "Tiptap vs Lexical vs Plate (2026)" — editor comparison, TipTap MIT-core/paid-cloud licensing — MEDIUM
- BlockNote docs (blocknotejs.org) + ProseMirror forum + GitHub (TypeCellOS/BlockNote) — MPL-2.0 licensing, block JSON model, ProseMirror/TipTap foundation — MEDIUM
- WorkOS "Top authentication solutions for FastAPI 2026" + FastAPI security docs — pwdlib/Argon2, JWT access/refresh patterns — MEDIUM
- patterns.dev "React 2026" + thetshaped.dev "Frontend Stack 2026" — TanStack Query + Vite + Tailwind + Zustand consensus — MEDIUM
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
