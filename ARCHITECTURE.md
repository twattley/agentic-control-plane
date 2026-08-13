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

## Tickets

A ticket is a markdown file in `tickets/` at the repo checkout root — thrashed
out in an interactive agent session, read-only to the control plane (no table;
`GET /repos/:id/tickets` lists the folder). The UI renders a ticket and "Start
work" creates a run with `ticket_id = <filename stem>`. Whenever a worker finds
`tickets/<ticket_id>.md` in the checkout, every role's prompt points at it —
the file, not the run title, is the spec.

**Ticket-writing is an interface with a freeze step**: discuss → freeze →
build. Freezing writes a `## Summary` section — two or three sentences aimed
at future-you re-entering cold (test scenarios follow it when they exist).
That summary is the re-entry blurb the **workbench** shows: `GET /board`
returns one pane per active run (run + repo name + frozen summary + last
event), grouped by project on the home page, runs waiting on the human first.
No `## Summary` → the ticket's first prose paragraph stands in.

## Agents

Who runs a pass is chosen **per run**: `runs.builder_provider` / `runs.reviewer_provider`
hold a provider spec — `provider[:model]`, e.g. `claude:sonnet`, `codex`, `stub` —
picked in the UI at "Start work" (NULL falls back to the global
`AGENTIC_CONTROL_PLANE_{BUILDER,REVIEWER}_PROVIDER` setting). The worker expands
the spec into CLI flags (`claude --model sonnet`, `codex exec -m …`). A manual
`POST /runs/:id/dispatch {"provider": …}` overrides the stored choice for one pass.

A Claude builder runs with `--permission-mode acceptEdits` by default — file edits
are auto-approved but unlisted Bash commands are refused; allowlist the repo's test
commands in the target repo's `.claude/settings.json`, or set
`AGENTIC_CONTROL_PLANE_CLAUDE_PERMISSION_MODE=bypassPermissions` to go full yolo.
A Codex pass is sandboxed by the CLI itself (`-s workspace-write`).

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
