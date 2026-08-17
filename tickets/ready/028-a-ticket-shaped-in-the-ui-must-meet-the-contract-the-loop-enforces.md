# Ticket 028: A ticket shaped in the UI must meet the contract the loop enforces

## Summary

The ideation surface already works end-to-end: `DiscussionPanel` bounces the
owner's idea off a resumed read-only `claude -p` session in the repo checkout
(`apps/api/app/services/discussion_agent.py`), and freeze has the plane write
the ticket. But the agent runs on a generic chat prompt ("ask one or two
questions, keep replies under 150 words") and `FREEZE_PROMPT` asks for only a
title, a `## Summary`, and `## Done means`. No scenarios, no `allowed_paths`,
no validation command — so a UI-born ticket arrives at the loop missing
exactly the sections the rest of the machinery enforces:
`scripts/check_ticket_scope` has no boundary to check, close has no
validation to run, and the protocol's "no declared write boundary, no
parallel work" rule makes the ticket second-class from birth.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped from the two-lanes conversation: the UI ideation
  surface exists and is in use, but its output doesn't meet the ticket
  contract the terminal lane enforces.
- Next: builder claims

## Why

The owner's stated workflow is two interchangeable lanes: shape and kick off
from the UI, or sit in terminal panes and drive the loop by hand. The lanes
only stay interchangeable if a ticket born in either lane is the same kind of
object. Today a terminal-shaped ticket carries scenarios, scope, and
validation; a UI-frozen one carries a summary and a wish. The gap also wastes
the strongest part of the discussion: the agent is *in the checkout* and can
read code while you talk — it is exactly the right party to propose a write
boundary and a validation command, and today it is never asked to.

Depth must follow size. A chore should freeze after one confirming bounce; a
feature deserves the grilling — scenarios, boundary cases, an explicit "should
not happen." One fixed interrogation depth would make the panel worse, not
better.

## Capability

A discussion in the UI runs the real shaping protocol. The agent first sizes
the request and matches its depth to it: small, well-bounded work gets a quick
confirmation and an early offer to freeze; fuzzy or larger work gets
Given/When/Then-style scenario thinking, one question at a time, each with a
recommended answer, grounded in files it actually read. By freeze time the
ticket carries what the loop enforces: a Summary, a Capability, a Scope block
with `allowed_paths` (and `forbidden_paths` where they earn their place), a
runnable Validation command, and checkable Done When items.

Freeze refuses to write a boundary-less ticket. If the discussion never
established `allowed_paths` or a validation command, freeze returns 422
naming what is missing, and the discussion stays open so one more bounce can
settle it — the plane does not silently bless an unshaped ticket because a
button was pressed.

## Public Interface

- `_SYSTEM` and `FREEZE_PROMPT` in `apps/api/app/services/discussion_agent.py`
  rewritten to carry the sizing-and-shaping protocol and the full ticket
  section contract. This is where the capability mostly lives.
- The freeze path in `apps/api/app/features/discussions/controller.py` gains a
  contract check on the agent's frozen markdown (presence of `allowed_paths`
  under a Scope section and a non-empty Validation section) before any file is
  written; failure is a 422 whose detail names the missing sections, and the
  discussion remains open.
- No web change: the panel already renders markdown replies and already keeps
  the discussion open on a failed freeze (error line, state untouched).

## Scope

- `allowed_paths`:
  - `apps/api/app/services/discussion_agent.py`
  - `apps/api/app/features/discussions/**`
  - `apps/api/tests/features/discussions/**`
- `forbidden_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/services/state_machine.py`
  - `apps/web/**`
- `depends_on`: none
- `parallelizable`: yes — disjoint from the worker tickets (027, 029) and the
  web ticket (026).

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] Freezing a discussion whose agent output carries Scope/`allowed_paths`
      and Validation writes the ticket exactly as today (both the legacy-slug
      and the story path).
- [ ] Freezing when the output lacks `allowed_paths` or a Validation section
      returns 422 naming the missing sections; no file is written and the
      discussion is still open (a further message succeeds).
- [ ] The freeze prompt demands the contract sections and the system prompt
      instructs sizing-proportional depth — pinned by tests on the prompt
      text, the same way `worker.py`'s task prompts are pinned.
- [ ] The agent subprocess is still read-only (no permission mode granted).

## Non-goals

- A depth knob in the UI — the agent judges size from the conversation; the
  owner can always overrule it in plain words ("this is a chore, just freeze
  it").
- Validating the *quality* of scenarios or the correctness of the proposed
  boundary — that stays human judgment at freeze time and reviewer judgment
  in the loop.
- Kicking off a run straight from freeze — hand-off to the loop remains its
  own explicit step.
