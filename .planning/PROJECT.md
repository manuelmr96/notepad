# Notepad

## What This Is

A self-hostable, containerized note-taking web app with a React frontend and a Python (FastAPI) backend. It starts as a simple multi-user notes app and grows, phase by phase, into a Notion-like workspace — block-based editing, nested pages, and structured databases/tables. Built for a solo developer who wants a clean, scalable foundation without premature infrastructure.

## Core Value

A logged-in user can reliably create, edit, and find their own notes — everything else builds on this foundation working flawlessly.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can create an account with email and password
- [ ] User can log in and stay logged in across sessions
- [ ] User can log out
- [ ] User can create a note with a title and text/markdown body
- [ ] User can view a list of their own notes
- [ ] User can open and read a single note
- [ ] User can edit an existing note
- [ ] User can delete a note
- [ ] Each user can only see and modify their own notes (data isolation)
- [ ] App runs fully containerized (frontend, backend, PostgreSQL) via Docker Compose for local dev
- [ ] Backend architecture is stateless and Kubernetes-ready (structured to scale horizontally later)

### Toward Notion (later phases — vision, not yet scoped into v1)

- [ ] Block-based editor (paragraphs, headings, lists as blocks; slash commands)
- [ ] Nested pages with infinite hierarchy and sidebar navigation
- [ ] Structured databases/tables (properties, views, filters)

### Out of Scope

- Realtime collaboration (live multi-cursor editing) — significant complexity; not part of the v1 vision, revisit after the block editor lands
- Mandatory third-party SaaS dependencies — must remain fully self-hostable
- Kubernetes manifests / cluster setup now — structure the app to be K8s-ready, but don't build orchestration infra until needed
- Mobile native apps — web-first; responsive web is sufficient

## Context

- **Greenfield project** — no existing code. Building from scratch in `/Users/manuelmoran/dev/personal/notepad`.
- **End-state north star:** something that feels like Notion by ~phase 5. Early architectural choices (data model, editor engine, page hierarchy) should not paint us into a corner for blocks, nesting, and databases.
- **Storage:** PostgreSQL — relational, well-suited to nested pages and the future structured-database feature; JSONB available for flexible block content.
- **Editor engine:** undecided — to be recommended during research (candidates: TipTap/ProseMirror, Lexical, Plate). Affects how the block model is structured in later phases.
- **Deployment:** Docker Compose for dev now; designed to be Kubernetes-ready for later cloud hosting. Hosting target deferred.
- **Solo developer** — phases must stay individually manageable; favor incremental, well-bounded scope.

## Constraints

- **Tech stack**: React frontend, FastAPI (Python) backend, PostgreSQL, Docker — fixed by the user up front.
- **Architecture**: Stateless API, containerized, horizontally-scalable-ready — the "scale as much as possible" goal means getting patterns right early, not building heavy infra now.
- **Self-hosting**: Must be fully self-hostable with no required third-party SaaS — user requirement.
- **Cost**: Prefer free/open-source tools and services — cost-sensitive solo project.
- **Team**: Solo developer — keep per-phase complexity manageable.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| React + FastAPI + PostgreSQL, containerized | Specified by user; mature, scalable, self-hostable, OSS | — Pending |
| Multi-user auth from Phase 1 | Notion-like end goal is inherently account-based; cheaper to build in early than retrofit | — Pending |
| Plain notes CRUD as Phase 1 MVP | Smallest useful version; validates the full stack end-to-end before adding complexity | — Pending |
| Defer realtime collaboration | High complexity, not core to the v1 vision; block editor matters more first | — Pending |
| K8s-ready but no manifests yet | "Scalable" via clean stateless architecture, avoiding premature infra cost/complexity | — Pending |
| Editor engine chosen during research | No strong preference; pick the best fit for a block model before committing | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-20 after initialization*
