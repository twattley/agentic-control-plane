# Handoff — 2026-08-17 (night)

The 015 → 014 → 016 arc from this morning is now actually closed, not just
reviewed. Tom's call: moving tickets from `in-progress/` to `complete/` by
hand "doesn't feel like the right step" once the tool exists to do it —
closing is an agent task, not a human one. So instead of a `git mv`, this repo
now runs its own portable kit and the three tickets went through the real
`scripts/close_ticket`, gate and all.

## What changed since this morning

**The kit is installed here** (`python3
~/Projects/agentic-engineering/scripts/install_repo_workflow --repo . --mode
link --apply`). `scripts/agent_workflow`, `scripts/close_ticket`,
`scripts/ticket_contract.py`, `scripts/check_ticket_scope`,
`scripts/check_ticket_conflicts` are now symlinks into `agentic-engineering`,
same as every other repo. `tickets/README.md` carries the contract marker.
`AGENTS.md` is filled in (test/lint/gate commands, the state-machine hazard,
and the fact that this repo dogfoods itself). `CLAUDE.md` was left alone —
it's repo-owned and the installer never overwrites a seed file that differs.

**015, 014, 016 closed for real.** Each ticket's `Phase` field said "review
done, awaiting human review" — descriptive, but not the contract's
`review-loop`, so `close_ticket` refused it (correctly — that's the refusal
acp-016 built). Fixed the Phase line on all three, then recorded the builder
pass and reviewer pass that had actually happened this morning into
`.agent-workflow/runs/` via `agent_workflow claim-ticket` / `post-findings`
(builder brief + reviewer verdict=pass, matching what the standards-reviewer
subagent actually found each round). Then ran the genuine
`./scripts/close_ticket <n> --gate-command "make test" --review-phase
review-loop` for each — real gate (`make test`, 179 pytest, ~34s), real
stamp, real lane move, real refusal path exercised along the way (legacy
tickets default to `--review-phase review` not `review-loop`, so the first
attempt on each correctly bounced until the phase matched). All three now
sit in `tickets/complete/`, stamped, with `run_file`/`run_id` recorded in the
close_ticket output.

This is the same mechanism acp-014's conformance suite proved works on a
symlinked test kit — now it's the real kit, in the real repo, closing real
work. Not committed yet (see below).

## Tom's framing — read this before doing more kit installs

Mid-close, Tom flagged something worth carrying forward: **this repo is the
overseer of the others, not a peer bound to their sequencing.** The other
repos run the builder/reviewer/closer loop *through* the control plane's API
— this repo *is* the control plane. Installing its own kit and dogfooding
`close_ticket` on itself is useful (it's the sharpest test of whether the
close path actually works), but that doesn't mean every future change here
has to march through the identical claim→build→review→close ledger dance the
way a downstream repo's ticket does. Judgment call for next session: keep
dogfooding for changes to the close/gate/reconciliation machinery specifically
(where "does this work on a real repo" is the actual question), and don't
feel obliged to run the full kit ceremony for things that are obviously just
this-repo maintenance.

## Start here

1. **Not yet committed.** `git status` on this repo right now: the three
   ticket moves (`in-progress/` → `complete/`, tracked as renames) plus the
   kit install artifacts (symlinks, `AGENTS.md`, `tickets/README.md`,
   `.gitkeep`s, `.agent-workflow/README.md`). `.agent-workflow/runs/` and
   `.agent-workflow/archive/` are already gitignored. Also still sitting from
   this morning: the three feature commits (015/014/016 code) and the evening
   handoff commit — four commits on `main`, unpushed. Review the diff, commit
   the kit-install + close, then push all of it together.
2. **Dogfood one real close on a downstream repo** —
   football-api-project is still the target: eight completed tickets a sweep
   would clear, a seeded gate, and a real `scripts/close_ticket` to delegate
   to. This exercises the acp-016 path from the *plane's* side (a run closed
   via the UI/API, not the terminal), which is the one this session didn't
   touch — everything above ran the terminal path.
3. Then the ready lane: `acp-013` (style bounce writes the convention down),
   `acp-018` (slow/broken gate strands a run in `closing`; also covers spawn
   OSError), `acp-019` (500-char truncation eats reviewer instructions; also
   covers tail-vs-head for gate output — higher stakes now that `gate_failed`
   feeds the fix round), `acp-030` (choose a skill when shaping; renumbered from acp-011).

## Repo state

| Repo | Branch | State |
| --- | --- | --- |
| agentic-control-plane | main | kit installed, 3 tickets closed via real `close_ticket`, **not committed**; 4 earlier commits unpushed |
| agentic-engineering | main | clean, untouched today |
| transcriber | main | 2 commits unpushed (from yesterday), 40 pytest |
| racing-platform | main | clean, pushed |
| football-api-project | main | 1 dirty file, not ours (`schema/seeds/2026-27-target-clubs.json`) |
| trading-platform | main | clean |

API + web restarted on the 015/014/016 code this morning; dev DB migrated
(006, `repos.close_gate_command`). Not restarted again tonight — nothing in
`apps/` changed, only tickets and kit scripts.

## Open work

**transcriber `E001-S00`** — still in `tickets/in-progress/`, reviewer verdict
`needs-work`, closed by the pre-017 bug. The gate is truthful now: decide
whether to re-run it through the plane or accept it. Its two unpushed commits
wait on that call. `E001-S01`/`S02` depend on it. **Discussion 5 is still
open** and will capture the "New ticket" button until closed.

## Known traps

- **Repos registered before acp-015 have no gate** until set once on the
  project page — they close ungated (visibly). Seeded: transcriber, racing,
  football, this repo. Not seeded: agentic-engineering, trading, others.
- **Agent messages are truncated to 500 characters** (`worker.py`). Ticketed:
  acp-019.
- **A gate/closer that hangs or can't spawn strands the run in `closing`**
  with no event. Ticketed: acp-018.
- **Ticket numbers collide across repos.** Two 015s/016s/017s exist. Say
  `acp-015` / `ae-015`, never a bare number.
- **A legacy (non-story) ticket's default `--review-phase` is `review`, not
  `review-loop`.** `close_ticket` picks the default from whether the ticket
  carries v1 story metadata, not from what its own `Phase:` field says. Pass
  `--review-phase review-loop` explicitly for tickets using the v1 vocabulary
  without full story front matter — 015/014/016 all needed it tonight.
- The conformance suite needs `~/Projects/agentic-engineering` (override
  `ACP_PORTABLE_KIT`; set `ACP_REQUIRE_PORTABLE_KIT=1` to fail instead of
  skip when absent).

## What actually worked

- The 3-ticket arc shipped in sequence this morning with the reviewer loop
  catching real defects each round: a backslash `re.error` in reconciliation,
  fence-unaware status stripping that silently ate content, historical runs
  misreported as ungated, the two close paths running gates under different
  shell rules, and closer refusals bouncing builders with no reason.
- Tonight's close proved the same thing from the other direction: the
  contract `close_ticket` enforces (exact `Phase: review-loop`, a completed
  reviewer pass in the ledger) is exactly the discipline described in the
  tickets' own Status blocks — it refused the first attempt on all three
  until the Phase line actually matched, which is the tool doing its job, not
  a bug to route around.
- The portable kit needed **zero changes** to install into a fourth repo or
  to close real work here — same result as acp-014 predicted.
