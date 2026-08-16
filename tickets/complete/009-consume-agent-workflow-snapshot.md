# Ticket 009: Consume the portable workflow snapshot

## Summary

The Control Plane currently scans only top-level `tickets/*.md` files and uses
the filename stem as both locator and run identity. Add a read adapter and
project view for `agent-workflow-snapshot-v1` so epics, stories, legacy work,
portable ledger runs, and diagnostics remain distinct while Control Plane runs
continue to link by stable work-unit identity after story moves or renames.

## Status

- State: complete
- Phase: closed
- Started: 2026-08-15 06:22 BST
- Updated: 2026-08-16 19:32 BST
- Completed: 2026-08-16 19:32 BST
- Last: 2026-08-16 19:32 BST - closed on a green gate: 139 pytest, ruff clean
  on apps/api/app and apps/api/tests, web build clean
- Next: none

## Capability

An operator opening a registered project can see its portable workflow as an
epic/story hierarchy with lifecycle state, coordination class, progress,
legacy work, portable handoffs, and diagnostics. Starting or revisiting work
uses the story's `story_id` or the legacy item's preserved `legacy_id`; the
current Markdown path remains a locator and may change without losing the
Control Plane run, prompt, or workbench summary.

## Public Interface

Add a read endpoint:

```text
GET /api/v1/repos/{repo_id}/workflow
```

The response is a typed Control Plane projection with:

- `source`: `agent-workflow-snapshot-v1` or `legacy-flat`;
- `schema_version`: the exact accepted snapshot version, or `null` only for
  the missing-adapter legacy fallback;
- the snapshot's `ticket_contract`, `epics`, `stories`, `legacy`, `runs`, and
  `diagnostics` collections without reinterpreting their identity fields.

Add a read endpoint for current Markdown content by stable identity:

```text
GET /api/v1/repos/{repo_id}/workflow/documents/{identity}
```

It returns the document identity, kind, current repository-relative path,
title, summary, and content. Resolution comes from the accepted snapshot, not
from a reconstructed filename. A locator must resolve to an existing Markdown
file below that checkout's `tickets/` root; absolute, escaping, missing, or
ambiguous locators are rejected rather than read.

The adapter invokes only this fixed command, without a shell, from the
registered checkout and with a bounded timeout:

```text
scripts/agent_workflow snapshot
```

A diagnostic-bearing snapshot may exit non-zero and is still a successful
read when stdout is valid `agent-workflow-snapshot-v1`. A present adapter that
times out, emits invalid JSON, or emits another schema version is an explicit
upstream error; it must not silently fall back to a flat scan.

When `scripts/agent_workflow` is absent, retain the current top-level
`tickets/*.md` behavior as `source: legacy-flat`. Do not label that fallback as
`agent-workflow-snapshot-v1`, invent epic/story identities, or recursively
discover nested work.

## Scenarios

### Show one portable workflow without parsing Markdown again

Given a registered repository emits a valid `agent-workflow-snapshot-v1` with
epics, stories across states, legacy work, portable runs, and diagnostics
When the operator opens the project
Then the API preserves the snapshot identities and diagnostics
And the web groups stories beneath their epic with progress
And state and coordination class are rendered as separate concepts
And legacy work and portable handoffs remain visible in explicitly labelled
sections.

### Preserve a Control Plane run through a story move

Given a Control Plane run has `ticket_id = E001-S02`
And the snapshot moves that story from
`tickets/ready/E001-S02-old-name.md` to
`tickets/in-progress/E001-S02-clearer-name.md`
When the project, workbench, builder, or reviewer reads the run
Then the run still links by exact `E001-S02`
And document detail, frozen summary, and agent prompt use the new locator
And neither the run's `ticket_id` nor its history is rewritten.

### Keep partial truth visible and unsafe work inert

Given the snapshot command exits non-zero with a valid document containing one
diagnosed story beside valid stories
When the operator opens the project
Then all readable records and diagnostics are displayed
And the diagnosed story cannot start a new Control Plane run
And no adapter code reparses the Markdown to guess a replacement identity.

### Preserve repositories that have not installed the adapter

Given a registered repository has no `scripts/agent_workflow`
And it has existing top-level legacy tickets and Control Plane runs
When the operator opens the project
Then the current flat ticket view and exact filename-stem run links still work
And the response is explicitly marked `legacy-flat`
And the read creates or changes no files in the checkout.

### Keep the two run systems distinct

Given a story has a portable file-ledger run and a Control Plane database run
with the same work-unit identity
When the project is rendered
Then both can be followed by exact identity
And their states are labelled as portable handoff versus Control Plane run
And they are not merged into one synthetic state machine or copied between
storage systems.

## Cases

| Case | Given | Expected |
|---|---|---|
| exact snapshot | command emits `agent-workflow-snapshot-v1` and exits zero | typed workflow response preserves all collections and reports snapshot source |
| diagnostics exit | command emits valid v1 JSON with diagnostics and exits non-zero | response remains usable and diagnostics stay visible |
| unsupported version | command emits a different `schema_version` | explicit upstream error; no flat fallback |
| invalid output | command emits malformed JSON or a structurally invalid v1 record | explicit upstream error; no partial identity guessing |
| timeout/failure | fixed command cannot complete within its bound | explicit upstream error with no mutation or fallback |
| missing adapter | checkout has no `scripts/agent_workflow` | only top-level Markdown is exposed as `legacy-flat`, with `schema_version: null` |
| epic grouping | stories reference a valid parent epic | stories group by exact `epic_id`; counts come from snapshot fields |
| empty epic | epic has zero stories | epic remains visible and is never startable |
| story presentation | story has state and coordination class | both labels render separately; path is not displayed as identity |
| stable story link | story locator changes but `story_id` does not | existing DB run, detail view, board summary, and prompts still resolve |
| portable run link | snapshot run has `work_unit_id = story_id` or `legacy_id` | run is shown under the exact matching identity and retains `ticket_kind` |
| orphan portable run | snapshot run has `ticket_kind: null` and diagnostic | run and diagnostic remain visible without fuzzy attachment |
| diagnosed story | story has non-empty `diagnostic_codes` | story remains visible but cannot start work |
| ready story | valid story is ready, builder-claimable, and has no active matching run | Start work creates a DB run whose `ticket_id` is exactly `story_id` |
| non-ready story | story is backlog, in-progress, blocked, or complete | no new-run control is offered |
| opted-in legacy | `ticket_contract` is `epic-story-v1` and legacy items remain | legacy section is readable and exact prior DB run links work, but no new legacy run is offered |
| migrating legacy | `ticket_contract` is null | existing legacy start behavior remains available and uses exact `legacy_id` |
| duplicate/unsafe locator | identity has multiple candidates, or path is absolute/escaping/missing | detail/prompt resolution refuses it and surfaces the problem; no file outside `tickets/` is read |
| bounded reads | several active DB runs belong to one repo | snapshot is loaded once per repo per board request, not once per run |
| read-only | workflow list/detail is requested | checkout paths and bytes are unchanged |

## Scope

```yaml
allowed_paths:
  - apps/api/app/features/workflow/**
  - apps/api/app/features/tickets/models.py
  - apps/api/app/features/tickets/repository.py
  - apps/api/app/features/tickets/controller.py
  - apps/api/app/main.py
  - apps/api/app/services/runs_service.py
  - apps/api/app/worker.py
  - apps/api/tests/features/workflow/**
  - apps/api/tests/features/tickets/test_tickets_api.py
  - apps/api/tests/features/runs/test_board.py
  - apps/api/tests/features/runs/test_task_spec.py
  - packages/domain-types/src/index.ts
  - apps/web/src/api/hooks.ts
  - apps/web/src/features/projects/ProjectView.tsx
  - ARCHITECTURE.md
  - tickets/ready/009-consume-agent-workflow-snapshot.md
  - tickets/in-progress/009-consume-agent-workflow-snapshot.md
  - tickets/complete/009-consume-agent-workflow-snapshot.md
read_context_paths:
  - CLAUDE.md
  - instructions/coding-standards.md
  - instructions/testing-instructions.md
  - apps/api/app/features/repos/**
  - apps/api/app/features/runs/**
  - apps/api/app/features/tickets/**
  - apps/api/app/services/executor.py
  - apps/api/tests/conftest.py
  - apps/web/src/features/runs/**
  - packages/domain-types/README.md
  - /Users/tomwattley/Projects/agentic-engineering/docs/adapter-snapshot-contract.md
  - /Users/tomwattley/Projects/agentic-engineering/docs/epic-story-workflow-contract.md
  - /Users/tomwattley/Projects/agentic-engineering/tickets/complete/006-expose-versioned-workflow-snapshot.md
forbidden_paths:
  - apps/api/schema/**
  - apps/api/app/features/discussions/**
  - apps/api/app/services/discussion_agent.py
  - apps/mobile/**
  - scripts/**
  - .planeignore
  - .env
  - .env.*
  - node_modules/**
  - /Users/tomwattley/Projects/agentic-engineering/**
  - /Users/tomwattley/Projects/football-api-project/**
  - ~/.claude/**
  - ~/.codex/**
  - ~/.agents/**
```

If implementing the stable document resolver proves to require a file outside
`allowed_paths`, stop and rescope this ticket before editing. `forbidden_paths`
override every allowed or read-context entry.

## Dependencies

- Complete: agentic-engineering ticket 006, commit `900d8cf`, which defines and
  emits the exact `agent-workflow-snapshot-v1` contract.
- Target repositories get the producer through the portable workflow install;
  this ticket does not install or copy that script into them.
- No dependency on agentic-engineering tickets 007 or 008. Those shared
  Claude/Codex consumers may be implemented concurrently.
- `parallelizable`: yes across repositories. Every implementation write is
  confined to `agentic-control-plane`, while tickets 007/008 write only in
  `agentic-engineering`. Within this repository this ticket owns the listed API,
  run-resolution, domain-type, and project-view surfaces and must not overlap
  another active Control Plane ticket touching them.

## Validation

Work test-first, one case at a time. Exercise the adapter through authenticated
HTTP routes using temporary registered checkouts and a temporary fixed
`scripts/agent_workflow` producer; do not depend on the developer's
`agentic-engineering` checkout or mock PostgreSQL.

Run from the Control Plane repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --project apps/api pytest apps/api/tests/features/workflow apps/api/tests/features/tickets/test_tickets_api.py apps/api/tests/features/runs/test_board.py apps/api/tests/features/runs/test_task_spec.py -v
make test
uv run --project apps/api ruff check apps/api/app apps/api/tests
npm --workspace @agentic-control-plane/web run build
git diff --check
git diff --name-only
```

The behavior suite must cover every cases row, including immutable pre/post
checkout trees, exact command selection without `shell=True`, rejection of
unsafe locators, and legacy fallback. Before review, confirm every changed path
is listed in `allowed_paths`; this repository does not currently provide an
automated ticket scope guard.

## Done When

- The Control Plane selects behavior by exact snapshot schema version and does
  not duplicate the v1 Markdown, lifecycle, progress, or run-linking rules.
- The project view visibly separates epics, stories, legacy work, diagnostics,
  portable handoffs, state, and coordination class.
- Epics are never startable; invalid and non-ready stories are inert; valid
  ready stories start DB runs with exact `story_id`; legacy start behavior is
  preserved only for repositories not opted into `epic-story-v1`.
- Existing Control Plane runs, board summaries, document reads, and every agent
  pass follow stable story or legacy identity to the current safe locator.
- Missing-adapter repositories retain their present top-level ticket behavior,
  while malformed or unsupported present adapters fail explicitly.
- Portable file-ledger runs and Control Plane database runs remain separate,
  read-only projections rather than silently synchronized storage.
- Backend tests, the full backend suite, Ruff, the web build, diff checks, and
  the manual scope audit pass.

## Non-goals

- Do not reimplement `epic-story-v1` Markdown parsing, progress derivation,
  claimability, diagnostic generation, or run linking in the Control Plane.
- Do not import portable ledger runs into PostgreSQL, export Control Plane runs
  to `.agent-workflow`, or merge their state machines.
- Do not add database tables or migrations.
- Do not create, migrate, rename, move, claim, close, or repair epic/story
  files. Canonical Control Plane authoring and lifecycle writes are later
  slices.
- Do not change the discussion/freeze flow or its APIs in this slice. The v1
  project view must not offer those legacy authoring controls.
- Do not add mobile screens, background polling workers, snapshot persistence,
  or cross-request caches.
- Do not execute a configurable command, invoke a shell, install workflow
  scripts into target repositories, or read a snapshot locator outside the
  registered checkout's `tickets/` root.
- Do not edit `agentic-engineering`, Football API, home runtime config, or any
  other repository.

## Follow-up Slices

1. Add Control Plane epic/story writers and lifecycle transitions against the
   accepted portable commands, including the discussion freeze path.
2. Pilot the accepted workflow and this adapter in Football API.
3. Revisit caching only after measuring snapshot latency across real projects.
