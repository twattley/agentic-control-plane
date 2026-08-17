# Ticket 033: Truncation must not eat an instruction the fix round needs

## Summary

Rescoped 2026-08-17: the original complaint — reviewer findings cut at 500
chars, a transcriber run 3 fix round spent on half a sentence — was largely
fixed by `7cd5768`, which gave reviewer summaries their own 4000-char budget
(`_FINDINGS_CHARS`, with the reasoning written down beside it). What remains
is the two ways a cut can still eat signal:

1. **Gate output keeps the wrong end.** Both `gate_failed` paths — the inline
   gate (`worker.py:372`) and the delegated closer refusal (`worker.py:395`)
   — do `[:500]`, keeping the HEAD of `stdout+stderr`. For a failing test
   suite the head is the platform banner; the failing test names and the
   assertion live in the TAIL. Since acp-016 these summaries feed the
   builder's next fix round directly, so the cut discards exactly the work
   order. (acp-025 carries reviewer findings past a *verdict* refusal, so
   that sub-case is covered; a red code gate is not.)
2. **Every cut is silent.** A reviewer summary over 4000 chars, or gate
   output over 500, is chopped mid-word with no marker — the builder cannot
   tell a complete instruction from a beheaded one.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17
- Updated: 2026-08-17 13:33
- Completed: 2026-08-17 13:33
- Last: close-ticket verified reviewer run cb1a20ea13241095 and close gate passed
  independent review standards-reviewer), verdict pass on round 2; round 1
  blocking fix: closer refusal clips stdout+stderr so the reason survives
  tail-keeping. 249 tests, ruff clean.
- Next: closed
  `apps/api/app/worker.py`, sequence behind 029, 031, and 032, which share
  the file.

## Why

A truncation bound exists so a rambling agent cannot stuff megabytes into an
event payload. That is the only job it has. A bound that keeps the banner and
drops the assertion, or that cuts without saying so, is doing a second job
nobody asked for: quietly degrading the very text the next pass runs on. The
doom-loop lesson from the E001-S01 lap applies here directly — a builder
acting on partial instructions burns a whole round producing the wrong fix.

## Capability

Gate-failure summaries keep the tail: when the combined output of a failed
gate or a closer refusal exceeds the budget, the worker keeps the END, where
pytest's failure summary and a closer's one-line reason both live. The budget
for gate output rises to something a real failure summary fits in (~2000
chars is enough for pytest's short-summary block; the builder judges the
exact number and writes the reasoning beside it, as `_FINDINGS_CHARS` does).

Every truncation is visible: any cut — findings, brief, or gate output —
lands on a whitespace boundary and carries an explicit marker (e.g.
`[… truncated]` / `[truncated …]` at the cut end) so a reader, human or
agent, always knows text is missing and from which end.

Reviewer findings and builder briefs keep their existing budgets and keep the
head — those numbers were reasoned recently and are not this ticket's
problem; only the silent-cut part touches them.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`: none
- `parallelizable`: no — shares `apps/api/app/worker.py` with 027 (active),
  029, 031, and 032.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] A failed inline gate whose output ends with pytest's short summary
      posts a `gate_failed` summary containing that tail, not the banner.
- [ ] A delegated-closer refusal keeps the tail of its output the same way.
- [ ] A reviewer summary over `_FINDINGS_CHARS` arrives cut on a whitespace
      boundary with a visible truncation marker; one under it arrives
      untouched, no marker.
- [ ] A pathological multi-megabyte payload is still bounded on every path.

## Non-goals

- Raising `_FINDINGS_CHARS` or `_BRIEF_CHARS` — both were sized deliberately
  in `7cd5768`; revisit only if a real run shows a complete review that
  doesn't fit.
- Storing full untruncated output as an artifact — if a truncated gate
  summary ever proves insufficient in practice, that's a follow-up ticket,
  not this one.
