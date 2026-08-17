# Ticket 031: A slow gate must not strand a run in closing

## Summary

The closer runs the repo's gate with a 1800s subprocess timeout, and
`subprocess.TimeoutExpired` is unhandled — a genuinely slow test suite raises
out of `_close_pass`, the worker dies, and the run sits in `closing` forever
with no event saying why. acp-015 made real per-repo gate commands the norm, so
long-running gates are now the expected case, not the edge.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 12:27:54 BST
- Updated: 2026-08-17 12:49
- Completed: 2026-08-17 12:49
- Last: close-ticket verified reviewer run ff658fd4e0bc505c and close gate passed
- Next: closed

## Capability

A gate that exceeds its time budget is a gate failure like any other: the run
routes to `needs_work` via `gate_failed`, and the event says the gate timed
out rather than that its tests failed. No run is ever left in `closing` with
no event explaining why.

Same class, added from acp-016's review: `OSError` on spawning the gate or the
repo's `scripts/close_ticket` (not executable, bad shebang) is equally
unhandled and strands the run the same way. Handle the family, not the one
symptom — `(OSError, subprocess.TimeoutExpired)`, as the workflow feature's
subprocess calls already do.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`: none
- `parallelizable`: no — shares `apps/api/app/worker.py` with 027 (active),
  029, 032, and 033.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] A gate command that exceeds the timeout produces `gate_failed` with a
      payload that names the timeout, and the run lands in `needs_work`.
- [ ] A test pins it (short timeout, `sleep` gate).
