# The workbench shows the split build handoffs

## Identity

- `kind`: `story`
- `story_id`: `E004-S02`
- `epic_id`: `E004`
- `coordination_class`: `feature`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: shaped from the split-builder workflow discussion
- Next: wait for E004-S00 and E004-S01

## Story

Tom can choose split mode and see who owns the run, what RED contract was
handed over, whether implementation preserved it, and what the reviewer said.

## Scenarios

### Scenario: Choose the split loop

Given a ready ticket
When Tom starts work in `Separate tests and implementation` mode
Then he can choose the test-author, implementer, and reviewer agents and the
created run records those choices.

### Scenario: See the current handoff

Given a split run at any waiting or active state
When Tom views the workbench or run detail
Then the label names the actual role and the detail shows the latest contract,
implementation, or review handoff without collapsing them into `builder`.

### Scenario: Ordinary runs stay compact

Given a direct or TDD run
When Tom views or starts it
Then the current two-agent controls and labels remain unchanged.

## Scope

- `allowed_paths`:
  - `apps/web/src/features/projects/ProjectView.tsx`
  - `apps/web/src/features/runs/RunDetail.tsx`
  - `apps/web/src/features/runs/StateBadge.tsx`
  - `apps/web/src/features/runs/Workbench.tsx`
  - `apps/web/src/features/runs/Inbox.tsx`
  - `packages/domain-types/src/index.ts`
  - `tickets/*/E004-S02-the-workbench-shows-the-split-build-handoffs.md`
- `read_context_paths`:
  - `apps/web/src/api/**`
  - `apps/api/app/features/runs/models.py`
  - `tickets/epics/E004-separate-test-design-from-implementation.md`
- `forbidden_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/services/**`
  - `tickets/*/E003-S01-*.md`
- `depends_on`:
  - `E004-S00`
  - `E004-S01`
- `parallelizable`: no; the visible states and artifact contract must land first.

## Validation

```bash
cd apps/web && npx tsc -b --noEmit
make test
scripts/check_ticket_scope tickets/in-progress/E004-S02-the-workbench-shows-the-split-build-handoffs.md
```

## Done When

- [ ] Split mode and three agent choices are available when starting work.
- [ ] The board and run detail name the current split role and expose its latest
      handoff artifact.
- [ ] Direct and TDD runs retain their current compact controls.
- [ ] Tom completes the ticket's short visual walkthrough.
