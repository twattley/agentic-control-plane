# Ticket 019: Truncation must not eat a reviewer instruction

## Summary

Agent messages are truncated to 500 characters in `worker.py` before posting.
On transcriber run 3 this ate a reviewer finding mid-word, and the builder
could not act on an instruction it never received — the fix round was spent
addressing half a sentence. Human notes are not truncated; the agents'
words deserve the same respect, or at least a bound the loop can survive.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped from the 2026-08-17 handoff's known-traps list
  ("not yet ticketed — worth doing")
- Next: builder claims

## Why

The reviewer's summary is not a log line: `_newest_instruction` feeds it back
to the builder verbatim as the fix instruction. Cutting it at 500 characters
cuts the actual work order. The bound exists so a rambling agent cannot stuff
megabytes into an event payload — the fix is a bound generous enough to carry
a real review (findings routinely run 1-3k chars), applied where display
needs it rather than where instructions are stored.

## Capability

The full reviewer verdict and builder brief reach the event payload intact up
to a generous bound (e.g. 10k chars, cut at a word boundary with an explicit
"… [truncated]" marker so a cut is visible, never silent). The builder's next
fix round receives the same text the reviewer wrote.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `depends_on`: none
- `parallelizable`: yes

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] A 3k-char reviewer summary reaches the builder's next task text intact.
- [ ] A pathological payload is still bounded, and the cut is marked, not
      silent.
