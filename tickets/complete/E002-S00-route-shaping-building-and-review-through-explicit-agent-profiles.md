# Route shaping, building, and review through explicit agent profiles

## Identity

- `kind`: `story`
- `story_id`: `E002-S00`
- `epic_id`: `E002`
- `coordination_class`: `platform`

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 14:44:21 BST
- Updated: 2026-08-17 15:04
- Completed: 2026-08-17 15:04
- Last: close-ticket verified reviewer run f28bddc3ff5ac4a8 and close gate passed
- Next: closed

## Story

Make the dogfood defaults deterministic at the process boundary. Shaping runs
Codex `gpt-5.6-sol` with high reasoning and priority service in a read-only
checkout; new builder/reviewer runs default to Claude Sonnet medium and Claude
Opus high. Per-run builder/reviewer pickers remain available for exceptions,
but shaping has no provider picker and never falls back to Claude.

Keep the existing request/response shaping lifecycle in this first slice. Its
purpose is to put the intended agents in charge and make failure semantics
safe before the durable turn lifecycle builds on top of it.

## Scenarios

### Scenario: Start and continue a Codex shaping discussion

Given a repository and no existing Codex session
When the owner sends the first shaping message
Then the subprocess is Codex `gpt-5.6-sol` with high reasoning and priority
service in the repository checkout under a read-only sandbox
And the reply text and Codex session id are recorded
And a later message resumes that exact Codex session with the same explicit
model, effort, service tier, and read-only boundary.

### Scenario: A selected shaping skill still frames Codex

Given the owner selected an installed shaping skill
When Codex handles the turn
Then the existing base shaping instructions and the selected skill are both in
the prompt
And Codex remains read-only.

### Scenario: Codex fails before the first reply

Given no completed discussion exists
When the Codex executable is missing, exits unsuccessfully, times out, or emits
an invalid response
Then the API returns the real sanitized failure
And no empty discussion row or message is retained
And retry starts a new Codex session.

### Scenario: Codex fails after completed conversation

Given a discussion already has completed messages and a Codex session id
When a later Codex turn fails
Then all prior messages and the session id remain unchanged
And retry resumes that same session.

### Scenario: An open discussion belongs to the former Claude shaper

Given an open discussion stores an unowned legacy Claude session id
When the owner tries to continue it after Codex becomes the shaping provider
Then the API explains that the discussion uses a legacy shaping session
And it does not pass that id to Codex or silently invoke Claude
And the completed legacy history remains readable.

### Scenario: New work uses the approved build and review defaults

Given the owner has not overridden either per-run picker
When a new run is created and dispatched
Then the builder command is Claude Sonnet at medium effort
And the reviewer command is Claude Opus at high effort
And choosing another offered provider for that run still overrides the default.

## Scope

- `allowed_paths`:
  - `tickets/in-progress/E002-S00-route-shaping-building-and-review-through-explicit-agent-profiles.md`
  - `apps/api/app/config.py`
  - `apps/api/app/services/discussion_agent.py`
  - `apps/api/app/features/discussions/controller.py`
  - `apps/api/app/features/discussions/repository.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/discussions/**`
  - `apps/api/tests/features/runs/**`
  - `apps/web/src/features/projects/ProjectView.tsx`
  - `apps/web/src/features/projects/__tests__/**`
  - `ARCHITECTURE.md`
- `read_context_paths`:
  - `packages/domain-types/src/index.ts`
  - `tickets/complete/027-dispatch-agents-at-a-chosen-effort.md`
  - `tickets/complete/030-choose-a-skill-when-shaping-a-ticket.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/schema/**`
  - `packages/domain-types/**`
  - `apps/web/src/features/projects/DiscussionPanel.tsx`
- `depends_on`:
  - none
- `parallelizable`: yes — the ready legacy ticket 035 is confined to
  `DiscussionPanel.tsx`; this story explicitly forbids that file.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [x] Command-contract tests pin initial and resumed Codex shaping to
      `gpt-5.6-sol`, high reasoning, priority service, and read-only access.
- [x] Codex JSONL is parsed into a non-empty final reply and resumable session
      id; missing, non-zero, timed-out, and malformed responses become clear
      API failures with no Claude fallback.
- [x] A failed first turn leaves no discussion or messages; a failed later
      turn leaves the existing discussion, messages, and session unchanged.
- [x] New session ids record Codex ownership; an unowned legacy Claude session
      is refused clearly without subprocess dispatch or history loss.
- [x] The default UI picker values and API worker defaults agree on Claude
      Sonnet medium for building and Claude Opus high for review.
- [x] Explicit per-run provider choices still override those defaults.

## Non-goals

- Streaming progress, cancellation, detached shaping workers, or reconnecting
  after navigation; those belong to E002-S01.
- A shaping-provider picker or automatic provider fallback.
- Changing skill discovery, freeze contract content, or the run state machine.
