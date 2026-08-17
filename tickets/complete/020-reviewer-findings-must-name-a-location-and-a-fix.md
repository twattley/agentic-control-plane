# Ticket 020: Reviewer findings must name a location and a fix

## Summary

The reviewer's task is one instruction: assess the diff and end with a
`VERDICT` line. Everything above that line is free prose — a finding might say
what's wrong, might say where, might say what to do about it, and the fix
round has to reconstruct all three from whatever the reviewer happened to
write. When the builder guesses wrong, the round is spent addressing the
wrong thing, and it costs a full lap to find out.

The pair is asymmetric on purpose: the reviewer (codex) is the stronger model.
Asking it to be vague so the builder has something to interpret wastes the
side of the pair that can already be precise. Every actionable finding should
read like a GitHub suggestion — a location and a proposed change — so the fix
round is "apply this" rather than "figure out what was meant."

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 09:02:14 BST
- Updated: 2026-08-17 09:30
- Completed: 2026-08-17 09:30
- Last: close-ticket verified reviewer run f1cec4dea1591e4c and close gate passed
- Next: closed

## Why

A prose finding like "the validation feels misplaced" survives a human
reviewer, who fills in the rest from context the transcript doesn't carry —
which file, which line, which specific change. The builder has no such
context; it only has the words. `013-a-style-bounce-writes-the-convention-down`
already recognises this failure mode for human notes ("the objection never
reached the builder") and fixes it by writing the rule down. This ticket fixes
the same failure mode at its more common source: the reviewer runs every
round, not just when a human intervenes.

The fix is on the input side of the pair, not the output side. Nothing here
weakens the pass case — a reviewer with nothing blocking still says so in one
line — it only raises the bar for what a *blocking* finding is allowed to look
like.

## Capability

Every actionable reviewer finding names a location (file, and a line or
function where that's meaningful) and a concrete proposed change, not just a
description of the problem. A finding that is a genuine judgment call with no
single correct fix (a design tradeoff, a scope question) is exempt — it still
names the location, but its finding is allowed to be a question rather than an
instruction.

The fix round receives findings already broken down by location, so the
builder's task is applying named changes rather than re-diagnosing the diff
from a paragraph.

## Public Interface

- The reviewer prompt built in `_task_for` (`apps/api/app/worker.py`) gains an
  explicit instruction: for each blocking finding, state the file (and
  line/function where applicable) and the specific change required, in
  addition to the existing `VERDICT: pass|changes` line. Judgment-call findings
  may be phrased as a question but must still be located.
- No new event type or payload field — findings still post through the
  existing `reviewer_findings_posted` summary. This changes what the reviewer
  is instructed to write, not how it's transported.
- `_newest_instruction`'s reviewer-findings branch is unaffected: the fix round
  still receives the findings text verbatim, which will now already carry
  location and suggestion.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
  - `apps/web/src/features/runs/RunDetail.tsx`
- `read_context_paths`:
  - `ARCHITECTURE.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`: none
- `parallelizable`: yes

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] The reviewer task text instructs blocking findings to name a location
      and a specific proposed change, pinned by a test on the composed prompt.
- [ ] A "nothing blocking" pass is unaffected — no location/suggestion is
      required when there is no finding to make.
- [ ] A judgment-call finding (no single correct fix) is still permitted, and
      still required to be located.
