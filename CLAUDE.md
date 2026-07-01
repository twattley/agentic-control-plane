# agentic-control-plane — Agent Entry Point

Read this first. It is the complete orientation for this project.

## What this project is

Portable agentic control plane for the builder/reviewer agent handoff loop — owns workflow state, locks, append-only events, artifacts, and approvals. Not an executor.

## Monorepo layout

```
apps/
  api/      Python FastAPI — business logic, SQL queries, CLI
  web/      React 19 + Vite — browser interface
  mobile/   Expo 54 + React Native — iOS/Android app
packages/
  domain-types/  TypeScript interfaces mirroring the Python Pydantic models
```

## Commands (run from repo root)

| Command | Does |
|---|---|
| `make serve` | FastAPI on :8400 |
| `make web` | Vite dev server on :5400 |
| `make mobile` | Expo (iOS sim or device) |
| `make init-db` | Apply schema/*.sql migrations |
| `make install` | uv sync + npm install |
| `make test` | pytest (backend) |

## Key architectural invariants — never break these

1. **Shared types live in `packages/domain-types/`** — TypeScript mirrors of Python Pydantic models
2. **No ORM** — raw asyncpg SQL in `repository.py` files only
3. **Controller-Service-Repository** — every feature splits across controller.py / repository.py / models.py
4. **TDD** — write the test first; see `instructions/coding-standards.md`
5. **Data contracts** — Pydantic at API boundaries; Python dataclasses for internal DTOs; pandas only for vectorised data

## Environment variables (`apps/api/.env`)

```
AGENTIC_CONTROL_PLANE_DATABASE_URL     — PostgreSQL connection string (required)
```

## Where to read next

- `ARCHITECTURE.md` — data model, design decisions
- `instructions/coding-standards.md` — TDD, contracts, patterns
- `instructions/testing-instructions.md` — pytest setup, fixture patterns
- `apps/api/README.md` — Python API structure
- `apps/web/README.md` — React app structure
- `apps/mobile/README.md` — Expo structure
- `packages/domain-types/README.md` — TypeScript contract
