# A blocked ticket must leave the agent loop without livelocking

## Identity

- `kind`: `story`
- `story_id`: `S003`
- `epic_id`: `none`
- `coordination_class`: `platform`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: found dogfooding football run 6 (E001-S06); ~5 builder↔reviewer cycles, no convergence
- Next: prioritise, then RED-first an agent-declared blocked disposition

## Story

When a ticket is genuinely blocked by an unmet dependency, the build⇄review
loop has no *early* agent-driven way out, so it grinds through the full
strike budget before the existing escalate-to-human backstop fires. The builder
posts a "blocked, nothing to do" brief (which still advances to
`awaiting_review`); the reviewer agrees it is blocked but its findings still
route back to `needs_work`; the builder is re-dispatched; repeat — a full Sonnet
build + Opus review burned on every lap until the backstop lands the run in
`awaiting_human`.

Observed on `football-api-project` run 6, ticket `E001-S06` (depends on
`E001-S05`, which is unbuilt in `backlog/`):

- ~5 builder→reviewer cycles across ~20 minutes (15:45 → 16:05), no progress,
  then the backstop escalated it to `awaiting_human`.
- Builder moved the ticket to `blocked/` on the *first* pass and stated plainly:
  *"the story can't be claimed in `blocked` state, so I'm summarizing directly."*
- Reviewer stated plainly on the *first* review: *"a human decision is needed
  before this can reopen."*
- Yet the state machine re-dispatched both roles four more times, because an
  agent that says "blocked" still emits a normal brief/findings event.

The backstop works but is far too slow: the signal ("both agents say blocked")
is present on the very first cycle. The only *fast* route to a stop today is a
human `block` decision. The loop should short-circuit to `blocked`/human the
moment a pass declares the ticket blocked, not ten agent passes later.

## Scenarios

### Scenario: A builder that cannot proceed halts the loop

Given a ticket with an unmet dependency
When the builder reports it cannot proceed (blocked)
Then the run moves to a non-dispatching state (`blocked`, or `awaiting_human`)
And no further builder or reviewer pass is auto-dispatched.

### Scenario: A reviewer confirming blocked routes to the human, not back to build

Given a builder pass that declared the ticket blocked
When the reviewer confirms it is blocked
Then the run routes to the human decision, not to `needs_work`.

### Scenario: Short-circuit on the first blocked declaration (should not happen)

Given a builder pass that declares blocked and a reviewer that confirms it
When the run is evaluated after that first cycle
Then it stops at `blocked`/`awaiting_human` immediately
And the run must NOT burn further builder/reviewer cycles waiting for the slow strike-out backstop to fire.

## Scope

- `allowed_paths`:
  - apps/api/app/worker.py
  - apps/api/app/services/state_machine.py
  - apps/api/tests/features/runs/
- `read_context_paths`:
  - apps/api/app/services/executor.py
  - apps/api/app/config.py
  - ARCHITECTURE.md
- `forbidden_paths`:
  - none
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
make test
```

A RED-first test that drives a run whose builder pass declares "blocked" and
asserts the run halts in a non-dispatching state with no further auto-dispatch;
plus a strike-out test that N no-progress laps escalate to `awaiting_human`.

## Done When

- [ ] A builder pass that declares "cannot proceed / blocked" moves the run to a non-dispatching state instead of `awaiting_review`.
- [ ] A reviewer confirming blocked routes to the human, not back to `needs_work`.
- [ ] The existing consecutive-no-progress strike-out remains as a backstop, but no longer the *first* line of defence.
- [ ] A ticket both agents agree is blocked stops after one cycle, not ~5.
- [ ] Covered by RED-first tests; `make test` green.
