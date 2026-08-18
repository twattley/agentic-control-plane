# Verification artifact for data slices is a real captured preview

## Identity

- `kind`: `story`
- `story_id`: `E003-S01`
- `epic_id`: `E003`
- `coordination_class`: `feature`

## Status

- State: complete
- Phase: done
- Started: —
- Updated: 2026-08-18 07:37
- Completed: 2026-08-18 07:37
- Last: close-ticket verified reviewer run 8a4527a7e7f1ed36 and close gate passed (non-independent review accepted by human)
- Next: closed

## Story

The second E003 artifact type, on the rail E003-S00 establishes: for a slice
that produces or transforms data, the verification artifact is a **real,
captured data preview** — a `head()` HTML table, dtypes, row and null counts, or
a small `describe()` summary — rendered inline in the approval pane. For a data
product this is the actual payoff to look at before approving: you trust a
NaN-free pipeline because you *saw* `head()` and the row count looked right, not
because tests passed.

The hard rule: the preview is **captured from executing the code**, never
composed by the agent. It reuses the plane's existing "actual outputs, never
claims" evidence discipline. A convincing but fabricated table is the worst
failure mode for data work, so the artifact must be traceable to a real run.

## Scenarios

### Scenario: A data slice shows a real captured preview

Given a builder pass that ingests or transforms data
When the run reaches `awaiting_human`
Then the pane renders a preview (e.g. `head()` as an HTML table plus row/null
counts) captured from running the code.

### Scenario: The preview is captured, not composed (should not happen)

Given a data preview artifact
Then its content must originate from executed code output, not model prose; a
preview that cannot be tied to a real run is a defect.

### Scenario: Oversized output is truncated legibly

Given a large result
When the preview is built
Then it is truncated to a sensible head/'…'/tail rather than dumping or lying
about scale.

## Scope

- `allowed_paths`:
  - apps/api/app/worker.py
  - apps/api/app/features/runs/models.py
  - packages/domain-types/**
  - apps/web/src/**
  - apps/api/tests/features/runs/**
- `read_context_paths`:
  - ARCHITECTURE.md
- `forbidden_paths`:
  - apps/api/app/services/state_machine.py
- `depends_on`:
  - E003-S00
- `parallelizable`: no

## Validation

```bash
make test
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [ ] A data slice's run carries a `verification` artifact holding a real
      captured preview (head/dtypes/counts), rendered inline in the approval pane.
- [ ] The preview is provably from executed output, not agent-composed.
- [ ] Oversized results are truncated legibly.
- [ ] `make test` green; `apps/web` TypeScript build clean.
