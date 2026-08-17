# Handoff — 2026-08-17 (evening)

The whole 015 → 014 → 016 arc landed in one session: per-repo close gates, a
portable-contract-clean ticket format pinned by a real-kit conformance suite,
and one implementation of close. Three commits on main, **not pushed** — all
three tickets sit in `tickets/in-progress/` awaiting your review, boxes
checked, review findings and accepted risks recorded in each Status block.

## Done today

**`acp-015` — the close gate belongs to the repo** (`26e1ae7`). Each repo
carries `close_gate_command` (nullable); the closer runs the run's repo's own
command in its checkout; an ungated close is recorded on the run and shown
amber, never as a green tick. `settings.close_gate_command` is gone and the
env var is out of `.env`. Registration suggests the repo's documented test
command (Makefile `test:` target, npm `test` script) and never invents one.
Set/edit/clear on the project page. Gates already seeded via the API:
transcriber `uv run pytest`, racing-platform `uv run python
scripts/verify_tests apps/etl`, football `uv run --active python -m pytest
apps/api apps/etl`, this repo `make test`. The rest show visibly ungated.

**`acp-014` — a plane-authored ticket closes with the portable closer**
(`3b1e1b9`). `_merge_story_body` reconciles an incoming `## Status` into the
skeleton's block (exactly one block; Started/Completed history carried into
placeholders; legacy phase vocabulary dropped; fenced examples left alone).
The builder prompt states the status contract for v1 stories — seven fields,
update never remove, `Phase: review-loop` at the review handoff. The
centerpiece is `test_portable_close_conformance.py`: it symlinks the REAL kit,
parses with the kit's own `ticket_contract.py`, and closes a plane-authored
story through the real `close_ticket` with zero hand edits. Every S001 repair
would fail it; so would a unilateral vocabulary change on either side.

**`acp-016` — closing in the plane runs the repo's own closer** (`8f2e9e6`).
A repo with `scripts/close_ticket` gets the full delegated close — gate,
stamp, lane move, aged-history sweep — then the plane's commit. The gate is
wrapped in `bash -lc` so both close paths obey the same shell rules. Refusals
surface verbatim as `gate_failed`, leave the run unclosed, and now feed the
builder's next fix round as its instruction (previously it was re-prompted
with stale findings and never told why). Compaction is exposed:
`POST /repos/{id}/workflow/compact` + a preview-then-confirm card on the
project page. The end-to-end test drives a plane run through the real
close_ticket: run closed, ticket stamped in `complete/`, lane move inside the
commit.

Every ticket went through the full loop: red first (verified by stashing the
fix), standards-reviewer pass, findings fixed or ticketed, gate green.

## Start here

1. **Human-review the three tickets** in `tickets/in-progress/` and move them
   to `complete/` (or bounce them). Then push.
2. **Dogfood one real close** — football-api-project is ideal: it has eight
   completed tickets a sweep would clear and a seeded gate. The first real
   delegated close will also exercise the refusal path honestly (the kit run
   file must exist, i.e. the builder must have claimed via the kit).
3. Then the ready lane: `acp-013` (style bounce writes the convention down),
   `acp-018` (slow/broken gate strands a run in `closing` — now also covers
   spawn OSError), `acp-019` (500-char truncation eats reviewer instructions —
   now also covers tail-vs-head for gate output; higher stakes since
   `gate_failed` feeds the fix round), `acp-011` (choose a skill when shaping).

## Repo state

| Repo | Branch | State |
| --- | --- | --- |
| agentic-control-plane | main | **3 commits unpushed**, tree clean. 179 pytest, ruff, tsc + build clean |
| agentic-engineering | main | clean, untouched today |
| transcriber | main | 2 commits unpushed (from yesterday), 40 pytest |
| racing-platform | main | clean, pushed |
| football-api-project | main | 1 dirty file, not ours (`schema/seeds/2026-27-target-clubs.json`) |
| trading-platform | main | clean |

API + web restarted on the new code; dev DB migrated (006, `repos.close_gate_command`).

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
- **Agent messages are truncated to 500 characters** (`worker.py`). Now
  ticketed: acp-019.
- **A gate/closer that hangs or can't spawn strands the run in `closing`**
  with no event. Ticketed: acp-018.
- **Ticket numbers collide across repos.** Two 015s/016s/017s exist. Say
  `acp-015` / `ae-015`, never a bare number.
- **agentic-control-plane still isn't registered in its own plane** (no kit
  installed), so these tickets were driven by hand. Installing the kit here is
  now more attractive: acp-014's conformance suite proves the plane's output
  closes cleanly, and acp-016 would give this repo the delegated close too.
- The conformance suite needs `~/Projects/agentic-engineering` (override
  `ACP_PORTABLE_KIT`; set `ACP_REQUIRE_PORTABLE_KIT=1` to fail instead of
  skip when absent).

## What actually worked

- The 3-ticket arc shipped in sequence with the reviewer loop catching real
  defects each round: a backslash `re.error` in reconciliation, fence-unaware
  status stripping that silently ate content, historical runs misreported as
  ungated, the two close paths running gates under different shell rules, and
  closer refusals bouncing builders with no reason.
- The red-check discipline (stash the fix, watch the tests fail on the S001
  defects) caught nothing wrong but proved the tests bite.
- The portable kit needed **zero changes** — the plane moved to the kit's
  vocabulary everywhere they disagreed, exactly as 014 prescribed.
