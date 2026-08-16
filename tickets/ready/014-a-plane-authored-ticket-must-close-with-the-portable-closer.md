# Ticket 014: A plane-authored ticket must close with the portable closer

## Summary

The control plane and the portable workflow kit share a repository, a ticket
format, and a run-ID scheme. They do not share a definition of the ticket. A
story this plane authors, and a status block its builder writes, cannot be
closed by `scripts/close_ticket` without hand-editing the file.

Nothing detects that, because every test on both sides uses a fixture written
by the same system that reads it. Pin the contract from the outside: a ticket
the plane creates and drives must satisfy the portable contract at every step.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-16
- Completed: —
- Last: 2026-08-16 - shaped after S001 needed four manual repairs to close
- Next: builder claims

## Why

Closing S001 — the first ticket taken end to end through the plane — required
four separate hand repairs, each surfacing only after fixing the last:

1. **Two `## Status` blocks.** `adopt_legacy` creates a skeleton story, then
   moves the legacy body in with its own status block. Tooling reads the first,
   which is the stale one.
2. **`Phase: review-ready`** written by the plane's builder, where
   `close_ticket` expects `review-loop`.
3. **`Started` missing** from the block the builder rewrites.
4. **`Completed` missing** from the same block.

Individually trivial. Together they mean the plane can drive work it cannot
finish, and a human has to edit markdown by hand at the last step of an
otherwise automatic chain.

This is invisible to both test suites — 138 tests here, 141 in
`agentic-engineering` — because neither takes a ticket through both systems.
Each side is internally consistent and they disagree with each other. That is
exactly the class of bug a conformance test exists for.

The plane's own closer is not a substitute: it commits and moves run state but
never touches the ticket's lane, so `complete/` stays empty unless the portable
closer runs.

## Capability

A story authored by the plane, adopted from a legacy ticket, and driven through
a full run satisfies the portable contract at every point a portable tool reads
it — exactly one status block, every required field present, and phase values
the portable closer recognises. Closing needs no hand-editing.

Where the two vocabularies genuinely differ, one side is corrected to match the
other rather than both being taught to tolerate the difference.

## Public Interface

- `adopt_legacy` produces a story with exactly one `## Status` block: the
  incoming legacy body's status is reconciled into the skeleton's, not appended
  beside it.
- The status block the plane's builder writes carries every field the portable
  contract requires, including `Started` and `Completed`.
- Phase vocabulary is reconciled with `close_ticket`'s expected review phase.
  The canonical name is whichever the portable contract already documents — the
  plane is the newer system and should move.
- A conformance test authors a story through the plane, applies the status
  transitions a run performs, and asserts the portable contract accepts the
  result — parsing with the same code `close_ticket` uses, not a copy of it.
- The test must fail if either side changes its vocabulary unilaterally.

## Scope

- `allowed_paths`:
  - `apps/api/app/features/workflow/repository.py`
  - `apps/api/app/features/workflow/models.py`
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/workflow/**`
  - `apps/api/tests/features/runs/**`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `tickets/complete/`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] A story adopted from a legacy ticket has exactly one `## Status` block.
- [ ] The status block written during a run carries `Started` and `Completed`.
- [ ] The phase the plane writes is the phase the portable closer expects, with
      the divergence resolved in one direction rather than both tolerated.
- [ ] A conformance test drives a plane-authored story through a run's status
      transitions and asserts the portable contract accepts it — using the
      portable parser, so a drift on either side fails the test.
- [ ] Closing a plane-driven ticket requires no manual edit to the file.
