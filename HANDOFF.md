# Handoff — 2026-08-16

First full day of dogfooding the control plane on real tickets. Two laps ran
end to end (racing-platform S001, transcriber E001-S00). Everything is
committed and pushed except where noted.

## Start here tomorrow

**Build `acp-017` first.** It is small, well-specified, and everything else is
misleading until it lands.

```
tickets/ready/017-an-escalated-rejection-must-not-be-recorded-as-a-pass.md
```

`worker.py:247` `_capped_verdict` rewrites a reviewer's `changes` to `pass`
once `max_review_rounds` is hit. The escalation routing is correct; the rewrite
is not. On transcriber run 3 the reviewer's last word was `VERDICT: changes`,
the plane recorded `pass`, the human approved what they were shown, and the
closer committed `5b316a2`. The portable `close_ticket`, reading the honest
ledger, still refuses to close that ticket.

So the plane can commit work its reviewer rejected. That is the bug to fix
before trusting another lap.

## Repo state

| Repo | Branch | State |
| --- | --- | --- |
| agentic-control-plane | main | clean, pushed. 139 pytest, tsc + build clean |
| agentic-engineering | main | clean, pushed. 163 unittest |
| transcriber | main | **2 commits unpushed**, tree clean, 40 pytest |
| racing-platform | main | clean, pushed |
| football-api-project | main | 1 dirty file, not ours (`schema/seeds/2026-27-target-clubs.json`) |
| trading-platform | main | clean |

Transcriber's two unpushed commits are the E001-S00 feature and the shaping
tickets. Left unpushed deliberately — see "open" below.

## Open work

**transcriber `E001-S00`** — in `tickets/in-progress/`, reviewer verdict
`needs-work`, but the plane closed run 3 and committed anyway (the acp-017
bug). The feature itself is sound: 40 tests green, focus checkbox works, the
duplicate-detection non-goal is preserved. Decide after acp-017 whether to
re-run it through a truthful gate or accept it.

`E001-S01` and `E001-S02` sit in `tickets/backlog/`, both depending on S00.

**transcriber discussion 5** is still `open` and never frozen, so it will
capture the "New ticket" button until it is closed — the same trap racing hit
this morning.

## Ready lane — agentic-control-plane

| Ticket | What |
| --- | --- |
| acp-013 | a style bounce writes the convention down |
| acp-014 | a plane-authored ticket must close with the portable closer |
| acp-015 | the close gate belongs to the repo, not the service |
| acp-016 | closing in the plane runs the repo's own closer |
| acp-017 | **an escalated rejection must not be recorded as a pass** |
| acp-011 | choose a skill when shaping a ticket (pre-existing) |

Sensible order: **017 → 015 → 014 → 016**. 017 makes verdicts honest, 015 makes
gates real per repo, then 014 and 016 close the two-closers seam.

## Known traps

- **The close gate is one global setting.** It is currently
  `AGENTIC_CONTROL_PLANE_CLOSE_GATE_COMMAND=uv run pytest`, correct for
  transcriber and wrong for every other repo. Change it by hand before a lap
  elsewhere and restart the API. This is acp-015.
- **Agent messages are truncated to 500 characters** (`worker.py:140`). This
  ate a reviewer finding mid-word on transcriber run 3, and the builder could
  not act on an instruction it never received. Human notes are *not* truncated.
  Not yet ticketed — worth doing.
- **The plane's closer does not move the ticket lane.** A closed run leaves its
  ticket in `in-progress/` forever. acp-016.
- **Ticket numbers collide across repos.** There are two 015s, two 016s, and
  two 017s. Say `acp-017` / `ae-017`, never a bare number.
- **agentic-control-plane is not registered** in the plane and has no kit
  installed, so its own tickets cannot be driven through its own UI.

## What actually worked

Worth remembering when it feels like a pile of bugs:

- Two models ran against each other unattended, many rounds, on two repos.
- The reviewer caught, unprompted: a spec violation (`headless` forwarding), an
  architecture breach, a **fabricated evidence table** where the builder
  reported test counts it had not run, a real regression (empty focus prompt),
  a scope breach, and a bug inside its own previous fix.
- Writing a convention into `.claude/instructions/data-pipeline.md` made the
  reviewer enforce it within minutes, having passed the same code twice before.
  The document outperformed every feedback channel — that is acp-013.
- `ae-017`'s diagnostics caught `unknown_phase` automatically, the first
  contract break all day that was reported rather than found by hand.
- Human `request_changes` now reaches the builder and gets acted on.
- transcriber went from no kit at all to a full gated lap in about an hour, and
  its test suite went 32 → 40.

## Yesterday's cleanup, for context

racing-platform went from 273 work items to 4, 15 diagnostics to 0, with 267
tickets compacted into `docs/DONE.md` and 195 runs archived. All three contract
repos are symlinked to canonical and on snapshot v2. transcriber is now the
fourth.
