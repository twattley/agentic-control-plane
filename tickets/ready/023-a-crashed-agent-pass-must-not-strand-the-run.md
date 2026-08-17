# Ticket 023: A crashed agent pass must not strand the run

## Summary

On run 4 a builder pass crashed after claiming — `CalledProcessError` out of
the worker's diff bookkeeping, because the (rogue, see `022`) pass had
committed everything and left nothing to diff. The worker process died before
posting any event. The run sat in `fixing` — a live-looking state — with
nothing anywhere telling a human it was dead. Only the worker log knew
(`FAILED run=4 role=builder`), and nobody reads the worker log from the UI.

`018` covers this trap on the closer/gate path. This is the same trap in the
builder/reviewer pass body, which has no wrapping at all: any exception
between claim and event-post kills the worker and freezes the run.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped from the live run-4 crash. The specific trigger
  is already gone — the revision-baseline rewrite (7cd5768) diffs against a
  persisted tree instead of re-applying a patch — but the class is untouched:
  nothing wraps `run_pass`, so the next unexpected exception strands the next
  run the same way.
- Next: builder claims. Sibling of `018`; consider whether one guard can
  serve both sites.

## Why

The run recovered tonight only because a human was watching the worker log
live and the next dispatch happened to succeed. Unattended — which is the
plane's whole premise — the run would still be sitting in `fixing`. A state
that means "an agent is working" must not be permanently occupied by an agent
that no longer exists.

## Capability

An exception escaping an agent pass posts a visible failure event on the run
— what died, in which role, with the error text — and the run lands in a
state a human can see and act on rather than a state that claims work is
still happening. No run is ever left in `building`, `fixing`, or `reviewing`
by a worker that is gone.

## Public Interface

- `run_pass` (`apps/api/app/worker.py`) gains a guard: post-claim failures
  record an event before the worker exits.
- The current state machine has no failure edge out of the active states, so
  `state_machine.py` is deliberately in `allowed_paths` this once. Add the
  minimal edge the capability needs; do not rework anything else, and keep
  every existing transition test green.
- The error text routed to a human is a report, not a fix instruction — it
  must not become the next builder round's task text (`_INSTRUCTION_SOURCES`
  stays as it is).

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/services/state_machine.py`
  - `apps/api/tests/**`
- `depends_on`: none
- `parallelizable`: no — touches the state machine other tickets forbid.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] A pass that raises after claiming posts a failure event with the error
      text, pinned by a test.
- [ ] The run ends in a human-visible state, not `building`/`fixing`/
      `reviewing`, pinned by the same test.
- [ ] All existing state machine tests pass unmodified.
