# agentic-control-plane — Architecture

> Portable agentic control plane for the builder/reviewer agent handoff loop — owns workflow state, locks, append-only events, artifacts, and approvals. Not an executor.

## Monorepo shape

```
apps/api/     Python 3.11 · FastAPI · asyncpg · PostgreSQL
apps/web/     React 19 · Vite · TanStack Query v5 · Tailwind CSS
apps/mobile/  Expo 54 · React Navigation v7 · TanStack Query v5
packages/     domain-types — shared TypeScript types
```

## What this is (and isn't)

A **control plane, not an executor.** It owns workflow state, role locks,
an append-only event log, artifacts, and human approvals. It never runs shell,
touches a repo, or edits code. Local workers (a later slice) poll it, claim a
run, invoke `codex exec` / `claude -p` inside their own checkout, and post
results back. The dangerous surface stays in the agent's own permission model.

## Data model

| Table | Holds |
|---|---|
| `repos` | Registered repositories (`slug`, `name`, local `path`) a run belongs to |
| `runs` | A unit of work + its current `state`; the run is the workflow aggregate |
| `events` | Append-only log of everything that happened on a run — the source of truth |
| `artifacts` | Attached outputs: `diff`, `test_output`, `screenshot`, `log` |
| `leases` | Role locks — at most one active (`released_at IS NULL`) lease per run+role |
| `decisions` | Human decisions: `approve`, `request_changes`, `block`, `close` |

Everything hangs off `runs` (FK, `ON DELETE CASCADE`). A run's history is
reconstructable from its events; the `state` column is a materialised cursor.

### State machine

The whole point of the control plane: run state can only move along legal edges,
enforced in `app/services/state_machine.py` (a `CHECK` constraint is the DB backstop).

```
queued ──builder claim──▶ building ──brief──▶ awaiting_review ──reviewer claim──▶ reviewing
                                                     ▲                                │
                                                     │                    findings    │
                          fixing ◀──builder claim── needs_work ◀──changes─────────────┤
                            │                                                          │
                            └──brief──▶ awaiting_review ─ ... ─▶ reviewing ──pass──▶ awaiting_human
                                                                                       │
                                                              human approve ──▶ approved ──close──▶ closed
```

`block` is legal from any active state → `blocked`. A state-moving event
releases the acting role's lease (builder hands off at `brief`, reviewer at
`findings`), so the next role can claim cleanly.

### Transitions are triggered by three surfaces

- `POST /runs/:id/claim` — a role takes a lease and moves the run into its working state
- `POST /runs/:id/events` — brief / findings / reply / note; some types move state
- `POST /runs/:id/decision` — the human's approve / request_changes / block / close

The **phone inbox** is three queue reads: `/queue/review`, `/queue/fix`,
`/queue/human` — "runs waiting on the reviewer / builder / you".

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
