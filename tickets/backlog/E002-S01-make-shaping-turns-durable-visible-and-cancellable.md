# Make shaping turns durable, visible, and cancellable

## Identity

- `kind`: `story`
- `story_id`: `E002-S01`
- `epic_id`: `E002`
- `coordination_class`: `feature`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: owner approved visible progress, cancellation, and reload survival
- Next: wait for E002-S00 and legacy ticket 035, then add RED lifecycle tests

## Story

Move each Codex shaping invocation out of the HTTP request and into a persisted,
detached turn lifecycle. The shaping panel shows truthful activity and elapsed
time, lets the owner cancel, and reconnects to the same turn after closing the
panel, navigating, refreshing, or hot-reloading the API. Conversation sends
and the final Create ticket turn use the same lifecycle so no agent call
returns to an opaque, uninterruptible spinner.

Persist pending input separately from completed discussion messages. A human
message and its agent reply become conversation history together only after a
successful turn. This keeps retries honest and makes a failed or cancelled
first turn removable without losing the draft that the UI needs to restore.

## Scenarios

### Scenario: A slow shaping turn visibly remains alive

Given Codex is processing a new message or Create ticket request
When the turn takes longer than an ordinary response
Then the panel shows its queued/running state, elapsed time, last activity
time, and a short lifecycle label derived from Codex JSONL
And it never displays hidden reasoning, a made-up percentage, or a hard
90-second deadline.

### Scenario: The owner cancels an active turn

Given a turn is queued or running
When the owner presses Cancel
Then the exact detached Codex process is terminated safely
And the turn becomes cancelled once, even if cancellation races completion
And prior completed messages and session id are unchanged
And the submitted text is restored as an editable draft for retry.

### Scenario: Initial failure or cancellation leaves no empty discussion

Given the turn is the first message for a proposed discussion
When it fails or is cancelled
Then the real sanitized error or cancelled state is visible
And no empty discussion row remains in the discussion list
And retry creates a fresh turn with no Codex session id.

### Scenario: Later failure preserves the resumable conversation

Given completed messages and a Codex session already exist
When a later turn fails or is cancelled
Then the prior history and session remain unchanged
And the failed input is restored
And retry resumes the same Codex session.

### Scenario: Leaving and returning reconnects instead of duplicating

Given a shaping turn is active
When the panel closes, the browser navigates or refreshes, or the API hot
reloads/restarts
Then the detached turn keeps running
And reopening the shaping panel discovers and reconnects to that same turn
And no second Codex process or duplicate human message is created.

### Scenario: A second submit is refused while one turn owns the discussion

Given a discussion has a queued or running turn
When another send, freeze, or duplicate request targets it
Then the API refuses it with a conflict and identifies the active turn
And the UI keeps a single progress and Cancel surface.

### Scenario: Successful turn commits atomically

Given Codex returns a valid final answer and session id before cancellation
When the worker completes the turn
Then the submitted human message and agent reply are appended together and the
session advances once
And a successful Create ticket turn writes and freezes exactly one ticket
through the existing contract checks.

### Scenario: Completion wins a late cancellation race

Given the successful result is already committed
When Cancel arrives late or is retried
Then the completed result remains canonical
And Cancel is an idempotent no-op rather than deleting history or a ticket.

## Scope

- `allowed_paths`:
  - `tickets/backlog/E002-S01-make-shaping-turns-durable-visible-and-cancellable.md`
  - `apps/api/app/features/discussions/**`
  - `apps/api/app/services/discussion_agent.py`
  - `apps/api/app/services/discussion_executor.py`
  - `apps/api/app/discussion_worker.py`
  - `apps/api/schema/**`
  - `apps/api/tests/features/discussions/**`
  - `packages/domain-types/src/index.ts`
  - `apps/web/src/api/hooks.ts`
  - `apps/web/src/features/projects/DiscussionPanel.tsx`
  - `apps/web/src/features/projects/__tests__/**`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/worker.py`
  - `apps/api/app/services/state_machine.py`
  - `tickets/ready/035-start-a-shaping-discussion-from-a-template.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/features/runs/**`
  - `apps/web/src/features/runs/**`
- `depends_on`:
  - `E002-S00`
- `parallelizable`: no — it owns the discussion API, persistence, agent seam,
  domain contract, and panel together. Legacy ticket 035 also changes
  `DiscussionPanel.tsx` and must land before this story is claimed.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
cd apps/web && npx tsc -b --noEmit
cd apps/web && npm test -- src/features/projects
```

## Done When

- [ ] A persisted turn model has explicit queued, running, succeeded, failed,
      and cancelled terminal semantics and permits at most one active turn per
      discussion or initial repo start operation.
- [ ] Agent work runs detached from Uvicorn and survives API hot reload/restart;
      process identity is validated before cancellation so an unrelated reused
      PID cannot be killed.
- [ ] Start, send, and freeze return promptly with a turn resource; status and
      cancel APIs are authenticated, repo-scoped, retry-safe, and tested.
- [ ] Codex JSONL updates coarse lifecycle activity without storing or exposing
      chain-of-thought, and terminal output/error is bounded and sanitized.
- [ ] The UI polls/reconnects to active work, shows state, elapsed and last
      activity, and exposes Cancel while the turn is active.
- [ ] Draft input clears only after success; failure/cancellation restores it,
      while completed messages and session data remain intact.
- [ ] Closing or refreshing the panel during a live turn neither cancels nor
      duplicates it; reopening reconnects to the same turn.
- [ ] First-turn failure/cancellation leaves no empty discussion; later failure
      preserves the existing discussion; successful messages and freeze commit
      exactly once.
- [ ] Tests cover duplicate submit, cancel-before-start, cancel-while-running,
      cancel-after-complete, worker failure, malformed output, API restart
      recovery, initial cleanup, later retry, and successful freeze.

## Non-goals

- WebSockets/SSE, percentage-complete estimation, token-by-token rendering, or
  a general agent telemetry framework.
- Exposing Codex reasoning text or raw unbounded subprocess output.
- Cancelling a turn merely because it crosses 90 seconds; an internal generous
  safety timeout may remain.
- Changing provider selection, the ticket markdown contract, run dispatch, or
  the run state machine.
