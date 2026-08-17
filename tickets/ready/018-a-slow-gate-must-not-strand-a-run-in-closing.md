# Ticket 018: A slow gate must not strand a run in closing

## Summary

The closer runs the repo's gate with a 1800s subprocess timeout, and
`subprocess.TimeoutExpired` is unhandled — a genuinely slow test suite raises
out of `_close_pass`, the worker dies, and the run sits in `closing` forever
with no event saying why. acp-015 made real per-repo gate commands the norm, so
long-running gates are now the expected case, not the edge.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped from acp-015's review pass (finding: pre-existing,
  but acp-015 is what makes slow gates likely)
- Next: builder claims

## Capability

A gate that exceeds its time budget is a gate failure like any other: the run
routes to `needs_work` via `gate_failed`, and the event says the gate timed
out rather than that its tests failed. No run is ever left in `closing` with
no event explaining why.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`: none
- `parallelizable`: yes

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] A gate command that exceeds the timeout produces `gate_failed` with a
      payload that names the timeout, and the run lands in `needs_work`.
- [ ] A test pins it (short timeout, `sleep` gate).
