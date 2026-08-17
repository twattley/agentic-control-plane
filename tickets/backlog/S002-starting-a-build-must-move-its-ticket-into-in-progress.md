# Starting a build must move its ticket into in-progress

## Identity

- `kind`: `story`
- `story_id`: `S002`
- `epic_id`: `none`
- `coordination_class`: `platform`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: found dogfooding transcriber run 5 (ticket S001-101); first approve failed the lane check
- Next: prioritise from backlog, then RED-first the deterministic lane move

## Story

When a run starts building, nothing deterministically moves its ticket file
from `tickets/ready/` into `tickets/in-progress/`. The move is left to the
builder *agent*, which does it inconsistently. As a result the first
human-approved close trips the closer's lane guard and the run is bounced back
through a wasted builder+reviewer cycle before it can land.

Observed on `transcriber` run 5 (ticket `S001-101-loop-test-banner-on-transcribe`):

1. build → review → pass → `awaiting_human`.
2. Human approved → closer refused:
   `Ticket must be in tickets/in-progress: …/tickets/ready/S001-101-….md`
   (`gate_failed` event, run routed back to `needs_work`).
3. The builder re-ran, this time moved the ticket `ready → in-progress`, and the
   run re-passed Opus review back to `awaiting_human`.

The plane self-heals, which is good, but it pays for a deterministic file move
with a full extra agent round-trip (tokens, latency, a spurious `gate_failed`).
The ticket's lane should reflect reality — "work has started" — the moment the
builder claims, independent of what the agent chooses to do.

## Scenarios

### Scenario: Claiming the builder lease moves the ticket into in-progress

Given a `ready` story with a Control Plane run
When the builder claims the run and the build begins
Then the ticket markdown is in `tickets/in-progress/` and the run state is `building`
And the move happened in the worker/close engine, not as an agent file edit.

### Scenario: A reviewed passing run closes on the first approve

Given a run whose ticket started in `ready`, built green, and passed an independent review
When the human approves it
Then the closer finds the ticket already in `tickets/in-progress/` and closes on the first attempt.

### Scenario: No wasted bounce just to relocate the file (should not happen)

Given the same reviewed passing run
When it is approved
Then the run must NOT emit a `gate_failed` whose only cause is the ticket lane
And it must NOT consume an extra builder+reviewer cycle purely to move the file.

## Scope

- `allowed_paths`:
  - apps/api/app/worker.py
  - apps/api/tests/features/runs/
- `read_context_paths`:
  - apps/api/app/services/executor.py
  - ARCHITECTURE.md
- `forbidden_paths`:
  - apps/api/app/services/state_machine.py
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
make test
```

A RED-first test that drives a run whose ticket starts in `ready`, claims the
builder, and asserts the ticket is in `tickets/in-progress/` with state
`building` — then that a subsequent pass + approve closes without a lane
`gate_failed`.

## Done When

- [ ] Claiming the builder lease deterministically moves the ticket `ready → in-progress` (worker/engine, not an agent edit).
- [ ] A reviewed, passing run whose ticket started in `ready` closes on the first approve.
- [ ] No `gate_failed` is emitted for the ticket lane alone, and no extra builder+reviewer cycle is spent relocating the file.
- [ ] Covered by a RED-first test; `make test` green.
