# Ticket 032: A style bounce writes the convention down

## Summary

When a human sends work back because it is *shaped* wrong rather than broken,
the fix today changes one file and teaches the system nothing. The next ticket
in that repo makes the same choice, and the human types the same objection
again.

A fix round that answers a style or convention objection must also record the
rule in the repository's own guidance. One correction, then the standard exists
— for the reviewer to enforce and for every later builder to read.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17
- Updated: 2026-08-17 13:04
- Completed: 2026-08-17 13:04
- Last: close-ticket verified reviewer run e235eace18224cbe and close gate passed
  independent review standards-reviewer), verdict pass on round 2; round 1
  warnings fixed: from_human flag replaces display-string discriminator,
  convention note grouped with plane-authored instructions.
- Next: closed

## Why

On the S001 lap the human objected to a source being wired into an ingestion
pipeline in the wrong idiom. The objection never reached the builder — the note
was empty and the prompt read from reviewer findings anyway. What *did* reach
it was a convention written into the repo's instruction files moments earlier.
The builder read the standard and refactored itself, unprompted.

So the durable artifact outperformed the feedback channel, and by a wide
margin: the note would have fixed one ticket, the document fixes every ticket
after it. That is the lever worth pulling automatically, because a human in the
middle of reviewing is exactly the person least likely to stop and write
documentation.

This is the capture step in a ladder the rest of which already exists or is
ticketed: written (repo instructions), reviewed (landed as acp-020), and tested (a repo's own
guard tests). All three are worthless if nothing ever gets written down.

## Capability

A builder addressing a human's requested change recognises when the objection
is about shape, structure, naming, or house style rather than a defect. In that
case the pass records the rule in the repository's own guidance alongside the
code fix, in the repo's existing format and location, and says so in its brief.

A correctness bounce is unaffected. A rule the repo already documents is not
duplicated — the builder is asked to check first and may reasonably conclude
nothing needs writing.

## Public Interface

- The fix-round prompt built by `_task_for`, when the instruction came from a
  human note (`human_note_posted`) rather than reviewer findings, gains an
  instruction: judge whether the objection is about convention rather than
  correctness, and if so record it in the repo's guidance as part of the fix.
- The wording is repo-agnostic — the builder is told to use whatever guidance
  location that repo already has, never a path this codebase chooses.
- It must be explicitly permissible to write nothing when the convention is
  already documented, so the prompt cannot manufacture duplicate rules.
- Reviewer findings prompts are unchanged: a reviewer enforcing a documented
  standard is not evidence of a missing one.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `read_context_paths`:
  - `ARCHITECTURE.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`:
  - none
- `parallelizable`: no — shares `apps/api/app/worker.py` with 027 (active),
  029, 031, and 033.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] A fix round driven by a human note asks the builder to record the rule in
      the repo's guidance when the objection is about convention, not a defect.
- [ ] A fix round driven by reviewer findings carries no such instruction.
- [ ] The prompt names no specific guidance path — it defers to the repo's own.
- [ ] The prompt permits writing nothing when the convention already exists.
- [ ] Tests pin both branches, so the instruction cannot be dropped or leak
      into the reviewer-findings path.
