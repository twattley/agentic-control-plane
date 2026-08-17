# Inbox shows clickable verify-URLs for a run's changed UI surfaces

## Identity

- `kind`: `story`
- `story_id`: `E003-S00`
- `epic_id`: `E003`
- `coordination_class`: `platform`

## Status

- State: ready
- Phase: queued
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped as the thin first slice of E003 (URL case)
- Next: builder

## Story

The thinnest observable slice of E003: when a run's builder pass changed one or
more frontend routes, the `awaiting_human` / inbox pane lists each changed page
as a **clickable `http://localhost:<dev-port><route>` link**, so the owner
clicks straight through to the running app to verify — instead of reading a diff
and guessing where the change shows up.

The URL is built from real repo facts — the Vite dev port and the actual route
in the router — never hardcoded or invented. The link list rides on the existing
run `artifacts` rail (a `verification` artifact), so the inbox just renders it.

Establishing this rail (the `verification` artifact shape + how the inbox shows
it) is why this slice is `platform`: later E003 slices add more artifact types
onto the same rail.

## Scenarios

### Scenario: A changed route becomes a clickable link

Given a builder pass whose diff adds or edits a frontend route (e.g. a new
`<Route path="lake" …>`)
When the run reaches `awaiting_human`
Then the inbox pane shows `http://localhost:<vite-dev-port>/<route>` as a
clickable link for that page.

### Scenario: Every changed surface gets its own link

Given a pass that touched two distinct routes
When the run reaches `awaiting_human`
Then both appear as separate clickable links, one per surface.

### Scenario: No viewable change is stated honestly, not faked

Given a pass that changed no frontend route
When the run reaches `awaiting_human`
Then the pane shows no verify-URLs and states there is no viewable surface —
it must not emit a guessed, empty, or hardcoded link.

### Scenario: The URL is derived, not invented (should not happen)

Given any pass that produces a verify-URL
Then the port comes from the repo's Vite config and the path from the router;
a link built from a hardcoded port or a route not present in the router is a
defect.

## Scope

- `allowed_paths`:
  - apps/api/app/worker.py
  - apps/api/app/features/runs/models.py
  - packages/domain-types/**
  - apps/web/src/**
  - apps/api/tests/features/runs/**
- `read_context_paths`:
  - apps/api/app/services/executor.py
  - apps/web/src/App.tsx
  - ARCHITECTURE.md
- `forbidden_paths`:
  - apps/api/app/services/state_machine.py
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
make test
cd apps/web && npx tsc -b --noEmit
```

Dogfood verify (meta): after a run lands at `awaiting_human`, open
`http://localhost:5400/inbox` — the changed-surface links appear on the waiting
pane. (This slice's own verify pointer is the feature it adds.)

## Done When

- [ ] A builder pass that changed one or more frontend routes yields, on the
      `awaiting_human` / inbox pane, a clickable `http://localhost:<dev-port><route>`
      link per changed surface.
- [ ] Port and route are derived from the repo (Vite config + router), not hardcoded.
- [ ] A run with no changed viewable route shows no links and says so.
- [ ] The links are carried as a run `verification` artifact on the existing
      artifacts rail, not an ad-hoc field.
- [ ] `make test` green; `apps/web` TypeScript build clean.
