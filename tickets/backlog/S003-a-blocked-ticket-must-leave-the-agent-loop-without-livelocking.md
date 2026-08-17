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
loop has no agent-driven way out, so it livelocks. The builder posts a
"blocked, nothing to do" brief (which still advances to `awaiting_review`); the
reviewer agrees it is blocked but its findings still route back to `needs_work`;
the builder is re-dispatched; repeat. The run ping-pongs indefinitely, burning a
full Sonnet build + Opus review on every lap, until a human notices and blocks
it by hand.

Observed on `football-api-project` run 6, ticket `E001-S06` (depends on
`E001-S05`, which is unbuilt in `backlog/`):

- ~5 builder→reviewer cycles across ~17 minutes (15:45 → 16:02), no progress.
- Builder moved the ticket to `blocked/` and stated plainly: *"the story can't
  be claimed in `blocked` state, so I'm summarizing directly."*
- Reviewer stated plainly: *"a human decision is needed before this can
  reopen."*
- Yet the state machine kept re-dispatching both roles, because an agent that
  says "blocked" still emits a normal brief/findings event.

The only route to `blocked` today is a human `block` decision (or a strike-out
that assumes a *failed* pass). Two agents agreeing "this is blocked" is neither,
so nothing terminates the loop.

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

### Scenario: Strike-out backstop (should not happen)

Given repeated passes that produce no forward progress
When a small consecutive-no-progress threshold is crossed
Then the run escalates to `awaiting_human`
And the run must NOT re-dispatch builder/reviewer indefinitely on a ticket both agents agree is blocked.

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
- [ ] A consecutive-no-progress strike-out escalates to `awaiting_human` as a backstop.
- [ ] No run can livelock builder↔reviewer on a ticket both agents agree is blocked.
- [ ] Covered by RED-first tests; `make test` green.
