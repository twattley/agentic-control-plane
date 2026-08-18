# Aider runs Gemini and DeepSeek builders without owning git history

## Identity

- `kind`: `story`
- `story_id`: `E005-S01`
- `epic_id`: `E005`
- `coordination_class`: `platform`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: portable writer created E005-S01
- Next: wait for E005-S00, install Aider deliberately, then add RED command-contract tests

## Story

Add Aider as one local builder runner behind the E005-S00 profile contract so
the same control-plane pass can use either a configured Gemini or DeepSeek
model. The runner is one-shot and starts from the frozen ticket/run context;
it may edit and validate the candidate but must never commit, clean, reset, or
absorb the owner's pre-existing checkout changes.

Keep Claude as the default through the 17 September 2026 subscription review.
This story makes alternatives runnable and selectable through the contract; it
does not change routing policy or automatically fail over a live pass.

## Scenarios

### Scenario: A Gemini profile runs through Aider

Given Aider is installed and the selected Gemini credential is configured
When a Builder pass resolves an enabled Aider/Gemini profile
Then the worker invokes Aider once with the exact configured model and ticket
instruction
And the resulting edits, summary, artifacts, and review handoff use the same
control-plane path as a Claude or Codex builder.

### Scenario: A DeepSeek profile uses the same runner contract

Given Aider is installed and the selected DeepSeek credential is configured
When a Builder pass resolves an enabled Aider/DeepSeek profile
Then only provider/model and selected credential differ from the Gemini command
And no DeepSeek-specific branch leaks into the run lifecycle or state machine.

### Scenario: Aider cannot own git history

Given the checkout may already contain scoped uncommitted work
When Aider executes a builder pass
Then auto-commits and dirty-checkout commits are disabled explicitly
And the existing before/after HEAD guard still reports any runner breach
And Aider does not create or modify repository configuration or history files
outside the ticket boundary.

### Scenario: A child sees only its selected secret

Given both Gemini and DeepSeek credentials exist in the API environment
When a Gemini pass is spawned
Then its child environment contains the Gemini credential but not DeepSeek's
When a DeepSeek pass is spawned
Then its child environment contains the DeepSeek credential but not Gemini's
And neither credential appears in argv, logs, events, artifacts, or API output.

### Scenario: An unavailable Aider profile fails before editing

Given the Aider executable or selected provider credential is missing
When dispatch preflights the profile
Then it returns a bounded actionable failure before acquiring an editing pass
And it does not silently invoke Claude, Codex, or another configured model.

## Scope

- `allowed_paths`:
  - `tickets/backlog/E005-S01-aider-runs-gemini-and-deepseek-builders-without-owning-git-history.md`
  - `ARCHITECTURE.md`
  - `apps/api/.env.example`
  - `apps/api/app/config.py`
  - `apps/api/app/services/agent_profiles.py`
  - `apps/api/app/services/agent_runners/aider.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/tests/features/agent_profiles/test_aider_runner.py`
  - `apps/api/tests/features/runs/test_agent_pass_failure.py`
- `read_context_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/services/runs_service.py`
  - `tickets/complete/023-a-crashed-agent-pass-must-not-strand-the-run.md`
  - `tickets/complete/026-a-flagged-builder-commit-must-reach-a-human-surface.md`
  - `tickets/complete/S004-a-run-must-never-stage-or-commit-changes-outside-its-ticket-boundary.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/features/discussions/**`
  - `apps/api/schema/**`
  - `packages/domain-types/**`
  - `apps/web/**`
- `depends_on`:
  - `E005-S00`
- `parallelizable`: yes — after E005-S00 lands, this story is confined to the
  Aider adapter, provider configuration, and adapter/failure tests; the
  E002-S02 profile-picker story can stay in frontend/API-presentation files.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] Aider implements the E005-S00 runner contract for Builder profiles and
      accepts configurable Gemini and DeepSeek model identifiers.
- [ ] Command-contract tests pin one-shot, non-interactive execution and
      mandatory no-auto-commit, no-dirty-commit, no-repository-config flags.
- [ ] The adapter passes only the selected provider credential in the child
      environment and tests prove the other configured credential is absent.
- [ ] Missing executable, missing credential, non-zero exit, timeout, and
      malformed/empty output use the existing bounded visible failure handoff.
- [ ] A fake local Aider executable proves successful edits and summaries flow
      through the ordinary builder artifact/review path without a network call.
- [ ] Claude remains the service and UI default; selecting Aider remains an
      explicit per-run choice.
- [ ] `make test`, Ruff, and the ticket scope guard pass.

## Non-goals

- Installing Aider implicitly at service startup or storing provider keys in
  the database.
- Making Aider a Reviewer or shaping-discussion runner in this slice.
- Benchmarking model quality, encoding current model rankings, or changing
  defaults based on latency.
- Automatic provider fallback after a pass begins or any checkout mutation.
