# Choose each run role's agent model and effort

## Identity

- `kind`: `story`
- `story_id`: `E002-S02`
- `epic_id`: `E002`
- `coordination_class`: `contract`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: owner approved per-run Agent / Model / Effort controls
- Next: add RED persistence and dispatch command-contract tests

## Story

Replace each role's combined agent picker with three explicit controls — Agent,
Model, and Effort — so the owner can reproduce the same deliberate profile from
the frontend that they would choose in a terminal. Builder and Reviewer are
configured independently, and their selections persist on the run so later fix
and review passes do not silently fall back to service-wide settings.

Keep `provider:model` as the internal provider compatibility seam. The UI
separates it into understandable controls and the run contract adds only the
missing per-role effort fields. Existing runs and API callers with no stored
effort continue to fall back to the service defaults introduced by E002-S00.

## Scenarios

### Scenario: The default profile is visible before a run starts

Given the owner opens a new run form
When they have not changed any agent controls
Then Builder shows Claude / Sonnet / Medium
And Reviewer shows Claude / Opus / High
And submitting the form persists those exact choices on the run.

### Scenario: Builder and Reviewer can be configured independently

Given the new run form is open
When the owner selects Codex / GPT-5.6 SOL / High for Builder
And leaves Reviewer as Claude / Opus / High
Then the builder pass runs `codex:gpt-5.6-sol` at high effort
And the reviewer pass runs `claude:opus` at high effort
And changing one role never changes the other role's controls.

### Scenario: Agent choice constrains the model list

Given a role's Agent control is Claude
When the owner opens Model
Then Sonnet and Opus are offered
When the owner changes Agent to Codex
Then GPT-5.6 SOL is offered and an incompatible Claude model is not retained
And choosing Stub disables or clears Model and Effort because neither applies.

### Scenario: Later passes retain the run profile

Given a run stores a builder and reviewer profile
When the builder enters a fix round or the reviewer is dispatched again
Then each detached worker receives that role's stored provider, model, and
effort
And a service restart or later global setting change does not alter the run's
stored profile.

### Scenario: Existing callers and runs remain compatible

Given an API caller omits the new effort fields or an older run stores null
When that role is dispatched
Then the worker uses the existing service-wide effort fallback
And existing `provider:model` values continue to parse unchanged.

### Scenario: A one-off provider dispatch does not erase the run profile

Given a run already stores a role effort
When the owner manually dispatches that role with a one-off provider override
Then the override changes only that pass's provider/model
And the stored role effort is used for the pass and remains persisted for the
next normal dispatch.

## Scope

- `allowed_paths`:
  - `tickets/backlog/E002-S02-choose-each-run-role-s-agent-model-and-effort.md`
  - `ARCHITECTURE.md`
  - `apps/api/schema/008_run_efforts.sql`
  - `apps/api/app/features/runs/models.py`
  - `apps/api/app/features/runs/repository.py`
  - `apps/api/app/features/runs/controller.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
  - `packages/domain-types/src/index.ts`
  - `apps/web/src/features/projects/ProjectView.tsx`
  - `apps/web/src/features/projects/AgentProfilePicker.tsx`
- `read_context_paths`:
  - `apps/api/app/config.py`
  - `tickets/complete/027-dispatch-agents-at-a-chosen-effort.md`
  - `tickets/complete/E002-S00-route-shaping-building-and-review-through-explicit-agent-profiles.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/features/discussions/**`
  - `apps/web/src/features/projects/DiscussionPanel.tsx`
- `depends_on`:
  - `E002-S00`
- `parallelizable`: no — E002-S01 also owns schema, domain types, and frontend
  API contracts; only one of these stories may be active at a time.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
cd apps/web && npx tsc -b --noEmit && npm run build
```

## Done When

- [ ] Builder and Reviewer each render Agent, Model, and Effort controls with
      defaults Claude/Sonnet/Medium and Claude/Opus/High respectively.
- [ ] Agent changes constrain the Model choices; Stub has no applicable model
      or effort and cannot submit stale hidden values.
- [ ] `builder_effort` and `reviewer_effort` are nullable persisted run fields
      mirrored through the API and TypeScript domain contract.
- [ ] Run creation, retrieval, board/list projections, and detached dispatch
      preserve each role's exact provider/model/effort selection.
- [ ] `_agent_command` prefers a supplied per-run effort and falls back to the
      existing role setting only when the run has none, for both Claude and
      Codex command spellings.
- [ ] A manual provider override uses the stored role effort without mutating
      the persisted run profile.
- [ ] Existing rows and clients with null/omitted effort keep today's global
      fallback behavior, pinned by a migration and regression tests.
- [ ] Tests cover both role defaults, independent selections, fix/review
      redispatch, null fallback, manual provider override, and Stub no-op.

## Non-goals

- Changing the shaping agent profile or adding provider controls to the
  discussion panel.
- Service-tier/priority selection, arbitrary custom CLI flags, or permission
  mode controls in the frontend.
- Dynamically discovering every model installed by either CLI; this slice uses
  the small dogfood catalog Claude Sonnet, Claude Opus, Codex GPT-5.6 SOL, and
  Stub.
- Changing run states, review routing, or the existing `provider:model` grammar.
