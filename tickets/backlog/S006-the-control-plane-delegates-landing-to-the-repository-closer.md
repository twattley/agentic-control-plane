# The control plane delegates landing to the repository closer

## Identity

- `kind`: `story`
- `story_id`: `S006`
- `epic_id`: `none`
- `coordination_class`: `platform`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: shaped after agentic-engineering Ticket 023 landed deterministic close
- Next: wait for E003-S01 to release apps/api/app/worker.py

## Story

When the control plane closes work in a repository with the portable closer,
that one command owns validation, scope, ticket movement, exact-path commit,
and the structured landing result. The plane does not make a second commit.

## Scenarios

### Scenario: Repository closer owns the landing commit

Given an approved run whose repository exposes the portable closer
When the control plane closes it
Then it invokes the closer in commit mode, records the returned hash, and marks
the run closed without calling its inline commit path.

### Scenario: A close failure remains recoverable

Given the gate, scope proof, move, or commit fails
When the closer returns non-zero
Then the run returns to `needs_work` with the substantive failure and no second
commit attempt.

### Scenario: Unrelated work remains untouched

Given unrelated staged or untracked checkout changes
When the delegated close lands the approved run
Then only the ticket-owned paths appear in the returned commit and unrelated
work remains exactly as it was.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/test_close_delegation.py`
  - `apps/api/tests/features/runs/test_close_boundary.py`
  - `tickets/*/S006-the-control-plane-delegates-landing-to-the-repository-closer.md`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `apps/api/app/services/state_machine.py`
  - `scripts/close_ticket`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/web/**`
  - `tickets/*/E003-S01-*.md`
- `depends_on`:
  - agentic-engineering `023-close-lands-reviewed-work-deterministically` (complete)
- `parallelizable`: no; it shares `worker.py` with active E003-S01.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/features/runs/test_close_delegation.py apps/api/tests/features/runs/test_close_boundary.py
make test
scripts/check_ticket_scope tickets/in-progress/S006-the-control-plane-delegates-landing-to-the-repository-closer.md
```

## Done When

- [ ] Delegated close passes `--commit` and trusts the returned landing hash.
- [ ] The plane does not run `_commit_and_close` after delegated landing.
- [ ] Failure returns the run to actionable `needs_work` without a second commit.
- [ ] Existing unrelated checkout changes survive unchanged.

## Non-goals

- Pushing from the control plane.
- Changing the fallback close path for repositories without a portable closer.
