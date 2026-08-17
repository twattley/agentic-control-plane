# Tickets

This repository uses the shared
[Portable Epic and Story Workflow Contract](https://github.com/twattley/agentic-engineering/blob/main/docs/epic-story-workflow-contract.md).
That document is canonical; this file records the local adoption marker and
commands.

## Contract

- `ticket_contract`: `epic-story-v1`

## Layout

```text
tickets/
  epics/        # outcome documents; not claimable
  backlog/      # stories not ready or not committed
  ready/        # scoped, startable stories
  in-progress/  # active stories and visible locks
  blocked/      # stories waiting on a decision or dependency
  complete/     # reviewed and closed stories
```

Epics use project-local IDs such as `E001`. Stories use IDs such as
`E001-S02`, and each story appears in exactly one state directory. The
human-readable filename suffix may change; identity may not. Claims,
dependencies, and run history use the story ID rather than the title, full
filename stem, or current path.

Files without valid v1 identity metadata remain visible as legacy/ungrouped
tickets. Do not silently assign IDs, rename files, or move completed history.

## Completed work

`complete/` is a lane, not an archive. Closing a ticket sweeps history older
than 30 days into the done ledger automatically (`--compact-after DAYS` to
change the window, `--no-compact` to skip). The ticket you just closed is never
swept. To sweep by hand:

```bash
scripts/agent_workflow compact --before <YYYY-MM-DD> --dry-run
```

Finished tickets become entries in `docs/DONE.md`; their runs move from
`.agent-workflow/runs/` to `.agent-workflow/archive/`. Compact tickets and
runs together — a ticket removed while its run stays behind becomes an orphan.
Files without a `Status` block are documents, not tickets, and are left alone.
Full original text stays in git history:

```bash
git log --diff-filter=D -- tickets/complete/<file>.md
```

## Story Status

```markdown
## Status

- State: in-progress
- Phase: queued
- Started: YYYY-MM-DD HH:MM
- Updated: YYYY-MM-DD HH:MM
- Completed: —
- Last: picked up
- Next: inspect current shape
```

`State` must match the containing directory. Builder and reviewer completion
are handoffs, not story completion:

- builder handoff keeps the story `in-progress` and points `Next` to reviewer;
- reviewer pass keeps it `in-progress` and points `Next` to close-ticket;
- close-ticket owns terminal status and the move to `complete`.

## Story Execution Metadata

Every story declares the identity, coordination class, boundary, and gate
required by the canonical contract. For example:

````markdown
## Identity

- `kind`: `story`
- `story_id`: `E001-S02`
- `epic_id`: `E001`
- `coordination_class`: `feature`

## Scope

- `allowed_paths`:
  - `src/example/**`
  - `tests/example/**`
- `read_context_paths`:
  - `docs/example.md`
- `forbidden_paths`:
  - `src/auth/**`
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
<repo test command>
```

## Done When

- [ ] <observable close condition>
````

`coordination_class` is `contract`, `platform`, `feature`, or `validation`.
It is technical routing metadata, not an epic or workflow state. A story that
cannot declare safe `allowed_paths` is not ready for parallel implementation.

## Gates

Before parallel work:

```bash
scripts/check_ticket_conflicts
```

Before review:

```bash
scripts/check_ticket_scope tickets/in-progress/<story-file>.md
```

Before close, validation and scope checks must pass or have an explicit
human-approved exception recorded in the story.
