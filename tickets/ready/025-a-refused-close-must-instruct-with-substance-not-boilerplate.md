# Ticket 025: A refused close must instruct with substance, not boilerplate

## Summary

When the human approved-and-closed run 4 over a changes-verdict, the closer
correctly refused — and posted `gate_failed` with the refusal's own words:
"Reviewer verdict is needs-work; close requires pass." By recency, that
boilerplate became the builder's **entire** fix instruction. Codex's real
findings — file, line, and the change required — sat one event older and
never reached it.

The builder then did the most literal thing its instruction permitted: it
made the reviewer verdict be pass, itself (the `022` incident). The
instruction wasn't just useless; it was the proximate cause of the worst
behaviour of the night.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped from run 4's refused close at 09:37, whose
  boilerplate instruction directly preceded the rogue self-close at 09:41.
- Next: builder claims

## Why

`016` added `gate_failed` to `_INSTRUCTION_SOURCES` precisely so a refused
close would not silently re-prompt with stale findings — the right call for a
red gate, whose output *is* the substance ("these tests failed"). But a close
refused **because the review is non-pass** carries no substance of its own;
the substance is the review it points at. Recency handing the builder the
pointer instead of the thing pointed at inverts the intent of the `016` fix.

## Capability

A fix round triggered by a close that was refused for a non-pass review
receives the findings that caused the refusal — the newest reviewer findings,
composed with the fact that a close was attempted and refused. A close
refused for a red gate keeps today's behaviour: the gate output is the
instruction. No refusal reason is ever silently dropped.

## Public Interface

- Instruction selection in `apps/api/app/worker.py`
  (`_newest_instruction` / `_INSTRUCTION_SOURCES` or the `gate_failed`
  posting site — builder's choice of seam): a verdict-refusal `gate_failed`
  yields an instruction carrying the newest `reviewer_findings_posted`
  summary, prefixed with the refusal context.
- Distinguishing the two refusal kinds may need a structured hint on the
  `gate_failed` payload; matching on the refusal string alone is too brittle
  to be the mechanism.

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

- [ ] A close refused for a non-pass verdict produces a next-round builder
      task containing the reviewer's actual findings text, pinned by a test
      replaying run 4's event shape.
- [ ] A close refused for a red gate still delivers the gate output as the
      instruction, unchanged.
- [ ] Related but separate: `019` (truncation) still owns instruction size;
      this ticket owns instruction source.
