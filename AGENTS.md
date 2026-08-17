# Repo Agent Guide

Local settings and hazards only. The workflow protocol, gate rules, and shared
commands are global — they live in `~/.codex/AGENTS.md`, synced from
`agentic-engineering`. Do not restate them here; a copy in this file is a copy
that drifts.

## Local Settings

Every line below must name a real value. Anything still in angle brackets means
this repo is not finished being installed.

- Test command: `make test`
- Lint/typecheck command: `uv run --project apps/api ruff check apps/api && cd apps/web && npx tsc -b --noEmit`
- Close gate command: `make test`
- Domain docs: `ARCHITECTURE.md`

Defaults that need no entry unless this repo differs: project slug is the repo
directory name, tickets are in `tickets/`, workflow files are in
`.agent-workflow/runs/`, and a work unit ID is the ticket filename without
`.md`.

## Local Hazards

- `apps/api/app/services/state_machine.py` — the run state machine. Frequently
  named `forbidden_paths` in tickets that touch the worker; edges out of
  `closing` are exactly `gate_passed`→closed and `gate_failed`→needs_work.
- This repo is itself the control plane other repos' agent loops report
  through — dogfooding a change here means the tool testing itself. Treat its
  own `.agent-workflow/` ledger and API/web restart as real, not a fixture.
