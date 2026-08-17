# Ticket 026: The plane dispatches agents at a chosen reasoning effort

## Summary

The provider spec already carries a model — `_split_spec` parses
`"provider[:model]"` and `_agent_command` passes it through as `--model`
(claude) or `-m` (codex), so choosing fable-5 is a `.env` flip today with no
code. What has **no** surface at all is reasoning effort: `_agent_command`
(`apps/api/app/worker.py:46`) emits no effort flag for any provider, so every
dispatched builder and reviewer runs at the CLI's default effort with no way to
raise it.

Both CLIs expose the knob, with different spellings:

- `claude --effort <level>` — a first-class flag (confirmed in `claude --help`).
- `codex exec -c model_reasoning_effort="high"` — a config override, not a
  dedicated flag. The exact key must be confirmed against `codex --help` /
  codex config docs before wiring; the `-c key=value` mechanism itself is
  confirmed.

Because fable-5 is a Claude model, the owner's immediate want — fable-5 at high
effort — rides entirely on the fully-confirmed `claude --effort` path.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped after confirming the model knob already exists and
  effort is the only missing lever; CLI flags for both providers pinned.
- Next: builder claims — but not while `worker.py` is held by an active
  ticket (see sequencing).

## Why

The plane's premise is unattended builder/reviewer runs. Reasoning effort is
the single biggest quality lever on those runs, and right now it is frozen at
each CLI's default with no operator control. Model is already selectable;
effort should sit right beside it as a peer knob, not require a code change
every time the owner wants a harder pass.

## Capability

An operator sets the reasoning effort each role's agent runs at, per role,
through configuration — the same seam that already carries provider and model.
`_agent_command` translates the chosen effort into the correct per-provider CLI
flag. An unset effort reproduces today's behavior exactly (no flag emitted), so
existing stub and real runs are unchanged until effort is deliberately set.

## Public Interface

- New settings fields `builder_effort` / `reviewer_effort`
  (`apps/api/app/config.py`), defaulting to `""` (unset = today's behavior),
  mirroring the existing `claude_permission_mode` precedent that `_agent_command`
  already consumes.
- `_agent_command` (`apps/api/app/worker.py`) appends the provider-appropriate
  effort flag when the field is set:
  - `claude` → `--effort <level>`
  - `codex` → `-c model_reasoning_effort="<level>"` (verify exact key first)
  - `stub` → ignored (no real agent).
- The provider spec grammar (`provider[:model]`) is unchanged; effort rides on
  the settings seam, not on the spec string, so no existing `.env` value or
  test that parses a spec needs to move.

## Scope

- `allowed_paths`:
  - `apps/api/app/config.py`
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`: none
- `parallelizable`: no — shares `apps/api/app/worker.py` with tickets `023`
  (active) and `024`. No logical dependency, but the scope guard is file-level,
  so this must be claimed only when `worker.py` is free. Claim it after `023`
  and `024` land, or rebase onto whichever lands first; the edits sit in
  `_agent_command`, a different function from both, so the merge is mechanical.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] With `builder_effort` set, a claude builder command includes
      `--effort <level>`, pinned by a test asserting the exact argv.
- [ ] With `builder_effort` set, a codex builder command includes the
      confirmed `-c model_reasoning_effort=<level>` override, pinned by a test.
- [ ] With effort unset, `_agent_command` emits no effort flag for any
      provider — the argv matches today's exactly.
- [ ] `reviewer_effort` drives the reviewer command independently of
      `builder_effort`.
- [ ] Setting effort on a `stub` provider is a no-op (no flag, no crash).

## Non-goals

- Selecting the model — already supported via the `provider[:model]` spec; this
  ticket adds no model machinery.
- Per-run or per-ticket effort overrides — this is a service-wide operator
  setting per role, matching how provider and permission mode already work.
- Validating effort values against a provider's allowed set; an unknown level
  is the CLI's error to report, not the plane's to police.
