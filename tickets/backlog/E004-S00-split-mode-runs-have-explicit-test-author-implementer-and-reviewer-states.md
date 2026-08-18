# Split-mode runs have explicit test-author implementer and reviewer states

## Identity

- `kind`: `story`
- `story_id`: `E004-S00`
- `epic_id`: `E004`
- `coordination_class`: `contract`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: shaped from the split-builder workflow discussion
- Next: wait for the portable split-build contract, then grill the lifecycle cases

## Story

Tom can start a `split-build` run whose persisted lifecycle and role leases
distinguish test authoring, implementation, and review, while existing `direct`
and `tdd` runs remain unchanged.

## Scenarios

### Scenario: A split run reaches each owner in order

Given a run created in `split-build` mode
When each role posts its successful handoff
Then the run waits for `test-author`, then `implementer`, then `reviewer`, and
finally Tom.

### Scenario: Contract problems return to the contract owner

Given an implementer or reviewer identifies a missing or incorrect executable
case
When the handoff targets the test contract
Then the run returns to `test-author` rather than asking the implementer to
rewrite tests.

### Scenario: Implementation problems return to the implementer

Given the contract is sound but the implementation is wrong
When the reviewer requests changes
Then the run returns to `implementer` with the existing contract intact.

### Scenario: Existing runs do not gain ceremony

Given a `direct` or `tdd` run
When it moves through the workflow
Then its builder/reviewer states, providers, events, and API shape remain
compatible.

## Scope

- `allowed_paths`:
  - `apps/api/schema/008_split_build_mode.sql`
  - `apps/api/app/config.py`
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/services/runs_service.py`
  - `apps/api/app/features/runs/models.py`
  - `apps/api/app/features/runs/repository.py`
  - `packages/domain-types/src/index.ts`
  - `apps/api/tests/features/runs/test_split_run_lifecycle.py`
  - `apps/api/tests/features/runs/test_run_providers.py`
  - `tickets/*/E004-S00-split-mode-runs-have-explicit-test-author-implementer-and-reviewer-states.md`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `apps/api/schema/**`
  - `apps/api/tests/features/runs/**`
  - `tickets/epics/E004-separate-test-design-from-implementation.md`
- `forbidden_paths`:
  - `apps/api/app/worker.py`
  - `apps/web/**`
  - `tickets/*/E003-S01-*.md`
- `depends_on`:
  - portable split-build ledger/role contract in `agentic-engineering`
- `parallelizable`: no; it establishes the states and API consumed by the
  worker and UI slices.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
cd apps/web && npx tsc -b --noEmit
scripts/check_ticket_scope tickets/in-progress/E004-S00-split-mode-runs-have-explicit-test-author-implementer-and-reviewer-states.md
```

## Done When

- [ ] Split mode has explicit waiting/active states for test authoring and
      implementation. Check: run the split lifecycle cases.
- [ ] Contract-targeted and implementation-targeted feedback route to different
      owners. Check: run the feedback rows.
- [ ] Per-run provider choices exist for all three agent roles. Check: create
      and fetch a split run through the API.
- [ ] Existing direct/TDD lifecycle cases remain green.

## Non-goals

- Executing agents or validating contract hashes.
- Adding the workbench controls.
