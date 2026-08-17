# Handoff — 2026-08-17

First full day of dogfooding the control plane on real tickets. Two laps ran
end to end (racing-platform S001, transcriber E001-S00). Everything is
committed and pushed except where noted.

## Done since the last handoff

**`acp-017` is closed** (`c56b2fd`). `_capped_verdict` is gone; verdict and
escalation are separate facts. `reviewer_findings_posted` carries the reviewer's
real verdict plus `escalated`, the state machine routes on the flag, and the run
view shows "✋ changes · rounds spent, over to you" instead of a green pass. The
plane can no longer show a rejection as an approval.

Two notes from doing it. The ticket had `state_machine.py` in `forbidden_paths`,
which made it impossible — `event_transition` is the only thing that reads the
verdict — so the scope was widened deliberately and recorded. And escalated
rejections now *count* as change rounds, where recording them as passes had
hidden them; a run that has already escalated returns to the human on the next
rejection rather than looping. Pinned by a test.

`max_review_rounds` is now **3**, not 2. On the first laps the third round was
repeatedly where a fix's own regression got caught.

## Start here

**`acp-015` — the close gate belongs to the repo.** It is the last thing making
every lap unsafe: one global command, correct for whichever repo is mid-lap and
wrong for the rest, currently `uv run pytest` for transcriber. Until it lands,
every lap needs a manual `.env` edit and an API restart, and forgetting means an
ungated close.

Then `acp-014` and `acp-016`, which close the two-closers seam together.

## Repo state

| Repo | Branch | State |
| --- | --- | --- |
| agentic-control-plane | main | clean, pushed. 145 pytest, ruff, tsc + build clean |
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
| acp-011 | choose a skill when shaping a ticket (pre-existing) |

Sensible order: **015 → 014 → 016**. 015 makes gates real per repo, then 014
and 016 close the two-closers seam. acp-017 is done.

## Known traps

- ~~**The close gate is one global setting.**~~ Fixed by acp-015 (2026-08-17):
  the gate lives on each repo (`repos.close_gate_command`, set on the project
  page or `PUT /api/v1/repos/{id}/gate`). The env var is gone. Repos registered
  before the change carry no gate yet — set each one once in the UI, or it
  closes visibly ungated.
- **Agent messages are truncated to 500 characters** (`worker.py:140`). This
  ate a reviewer finding mid-word on transcriber run 3, and the builder could
  not act on an instruction it never received. Human notes are *not* truncated.
  Not yet ticketed — worth doing.
- ~~**The plane's closer does not move the ticket lane.**~~ Fixed by acp-016
  (2026-08-17): a repo with `scripts/close_ticket` gets the full delegated
  close — gate, stamp, lane move, sweep — then the plane's commit. Repos
  without the kit keep the inline gate-and-commit.
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
