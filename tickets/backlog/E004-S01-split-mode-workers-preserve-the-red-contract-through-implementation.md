# Split-mode workers preserve the RED contract through implementation

## Identity

- `kind`: `story`
- `story_id`: `E004-S01`
- `epic_id`: `E004`
- `coordination_class`: `platform`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: shaped from the split-builder workflow discussion
- Next: wait for E003-S01, E004-S00, and the portable role methods

## Story

The control-plane worker dispatches the portable `test-author` and `implementer`
methods, publishes a machine-readable RED contract, and refuses an
implementation pass that changes that contract.

## Scenarios

### Scenario: Test author leaves executable RED evidence

Given a split-mode ticket with declared test paths
When the test-author pass completes
Then the plane records the exact contract paths and hashes, the command it ran,
and output proving the intended failure rather than a broken fixture.

### Scenario: Implementer receives a frozen contract

Given a recorded RED contract
When the implementer is dispatched
Then its task includes that contract and tells it to make the cases green
without editing the contract paths.

### Scenario: Contract mutation is refused

Given an implementer changes a hashed contract path
When its pass ends
Then the plane records the violation and does not hand the run to review.

### Scenario: Green evidence reaches review

Given the implementer leaves the contract unchanged and makes it green
When the reviewer is dispatched
Then the reviewer receives the original RED evidence, current hashes, green
gate output, and the implementation diff.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/test_split_worker.py`
  - `apps/api/tests/features/runs/test_role_method.py`
  - `apps/api/tests/features/runs/test_agent_pass_failure.py`
  - `tickets/*/E004-S01-split-mode-workers-preserve-the-red-contract-through-implementation.md`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/features/runs/**`
  - `tickets/epics/E004-separate-test-design-from-implementation.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/web/**`
  - `tickets/*/E003-S01-*.md`
- `depends_on`:
  - `E004-S00`
  - portable test-author/implementer skills in `agentic-engineering`
- `parallelizable`: no; `apps/api/app/worker.py` is currently owned by E003-S01
  and this slice consumes E004-S00's lifecycle.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
scripts/check_ticket_scope tickets/in-progress/E004-S01-split-mode-workers-preserve-the-red-contract-through-implementation.md
```

## Done When

- [ ] A real test-author pass produces a validated RED-contract artifact.
- [ ] A real implementer pass receives the contract and cannot alter its files.
- [ ] Missing, malformed, stale, or already-green contract evidence blocks the
      handoff. Check: run the negative contract cases.
- [ ] A valid green implementation hands the original contract and diff to the
      reviewer.

## Non-goals

- Choosing the behavior on the owner's behalf.
- UI presentation of the new handoffs.
