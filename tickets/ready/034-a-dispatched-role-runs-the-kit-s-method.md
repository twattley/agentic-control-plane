# Ticket 034: A dispatched role runs the kit's method

## Summary

The plane's `_task_for` composes each role's prompt from scratch, and its
copy of the role method has diverged from the kit's skills — the located-
findings demand (acp-020) and the builder boundary (acp-022) exist only
here, while terminal sessions run the kit's version without them. ae-022
moves the method into lane-agnostic `ROLE.md` files beside the kit's builder
and reviewer skills. This ticket makes the worker consume them: a dispatched
pass's prompt becomes the kit's role method plus the plane's own harness
contract, and the inline duplicate is deleted.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 12:33 BST - dependency satisfied: ae-022 closed (kit
  commit 80e72a2) and synced to both installed layers (~/.claude/skills and
  ~/.agents/skills — the codex-visible path, useful when implementing).
- Next: builder claims — once the worker lane (029/031/032/033) has drained
  `apps/api/app/worker.py`; this ticket goes last by design.

## Why

The owner's ruling on layers: the kit owns the roles, the plane owns the
run. Everything portable about how a builder builds and a reviewer reviews
belongs in agentic-engineering, where one edit (plus `scripts/sync`) reaches
terminal panes and plane runs together. What stays here is what only the
plane can know: this run's ticket, the newest instruction, the diff under
review, the evidence invitation, and the machine-readable output contract
its parsers depend on.

## Capability

For a builder or reviewer pass, the worker reads the role's method from the
installed skill layer — `~/.claude/skills/<role>/ROLE.md`, the same runtime
truth the shaping dropdown (acp-030) reads, deliberately not the kit repo —
and composes the prompt as: role method, then run context, then the
harness contract. The harness contract stays plane-owned and inline:

- the ticket reference, spec note, and newest instruction (builder), or the
  diff and evidence note (reviewer);
- the exact `VERDICT: pass` / `VERDICT: changes` final-line format
  `_parse_verdict` greps for;
- the `SUMMARY:` headline convention `_headline` reads;
- the status-contract and evidence-invitation notes.

A missing or empty ROLE.md fails the pass loudly — the pass errors with an
event naming the missing file and the run routes through the existing
failure path (acp-023's guard), never a silent fallback to nothing or to a
stale inline copy. The role text the plane no longer owns is deleted from
`worker.py`, and the tests that pinned its wording move with it: plane tests
now pin the seam (ROLE.md content present in the composed prompt, harness
contract intact), while the kit's tests pin the words (ae-022).

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/config.py`
  - `apps/api/tests/features/runs/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`:
  - ae-022 (kit: `ROLE.md` files exist and are synced)
- `parallelizable`: no — shares `apps/api/app/worker.py` with 029, 031,
  032, 033. Claim last: it deletes prompt text those tickets' tests may
  touch, so it rebases cheapest at the back of the worker lane.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] A builder pass's composed prompt contains the installed builder
      ROLE.md body followed by the plane's run context and harness contract;
      a reviewer pass likewise — pinned by tests using a temp skill dir.
- [ ] The VERDICT and SUMMARY output contracts are composed by the plane,
      not read from the kit, and their parsers are unchanged.
- [ ] With ROLE.md missing, the pass fails with an event naming the file,
      and the run lands where a crashed pass lands today — no silent
      fallback.
- [ ] The duplicated role-method text (located-findings wording, builder
      boundary note) is gone from `worker.py`; the plane's tests assert the
      seam, not the kit's words.
- [ ] The skill-layer location is configurable only insofar as tests need a
      temp dir — no new operator knob.

## Non-goals

- Changing the shaping surface — acp-030 already consumes whole skills for
  discussions; this ticket touches only the two loop roles.
- Injecting ROLE.md for the closer — close is a script call, not a prompt.
- Per-repo or per-run role overrides; one method per role per host, by
  design.
