# agentic-control-plane — Architecture

> Portable agentic control plane for the builder/reviewer agent handoff loop — owns workflow state, locks, append-only events, artifacts, and approvals. Not an executor.

## Monorepo shape

```
apps/api/     Python 3.11 · FastAPI · asyncpg · PostgreSQL
apps/web/     React 19 · Vite · TanStack Query v5 · Tailwind CSS
apps/mobile/  Expo 54 · React Navigation v7 · TanStack Query v5
packages/     domain-types — shared TypeScript types
```

## Data model

_Fill in entity descriptions and relationships here._

## Feature layout

Each backend feature lives at `apps/api/app/features/<name>/`:

| File | Responsibility |
|---|---|
| `controller.py` | FastAPI router — routes only, no business logic |
| `repository.py` | asyncpg SQL queries |
| `models.py` | Pydantic request/response models + internal dataclasses |

## Storage

- **Primary** — PostgreSQL (all structured data)
- **Secondary** — S3 (blobs, large files, exports) — add when needed

## SQL migrations

Numbered files in `apps/api/schema/`. Applied in sort order at startup via `make init-db`.

## Frontend state

TanStack Query owns all server state. Local UI state stays in component or context.
