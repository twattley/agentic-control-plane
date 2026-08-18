# Dispatch resolves an explicit runner-neutral agent profile

## Identity

- `kind`: `story`
- `story_id`: `E005-S00`
- `epic_id`: `E005`
- `coordination_class`: `contract`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: portable writer created E005-S00
- Next: wait for E003-S01 review/close, then add RED profile-contract tests

## Story

Give dispatch one explicit agent-profile contract that distinguishes the CLI
runner from the model provider, model identifier, and supported reasoning
effort. Persist the resolved Builder and Reviewer profiles on the run so later
passes are reproducible, while translating existing `provider:model` rows and
callers through a compatibility boundary. Move current Claude, Codex, and Stub
command construction, child-environment contribution, capability declaration,
and final-output decoding behind runner adapters. The worker consumes only the
normalized contract and contains no runner/provider-name dispatch branches.

This is the contract prerequisite for provider integrations. It must preserve
the current Claude defaults through the 17 September 2026 subscription review
and must not add Gemini, DeepSeek, Aider, or automatic fallback itself.

## Scenarios

### Scenario: A new run persists resolved role profiles

Given the owner starts a run with explicit Builder and Reviewer selections
When the run is created
Then each role stores a resolved runner, provider, model, and applicable effort
And later fix or review passes use that stored snapshot rather than a changed
service default or mutable catalog entry.

### Scenario: Existing runs and callers remain dispatchable

Given an existing run or API caller supplies `claude:sonnet`, `codex`, or
`stub` through the current provider fields
When dispatch resolves its role profile
Then the compatibility boundary produces the same Claude, Codex, or Stub
command semantics used today
And omitted selections still resolve to Claude Sonnet medium for Builder and
Claude Opus high for Reviewer.

### Scenario: Today's runners prove the extension boundary

Given Claude, Codex, and Stub are the only configured runners
When any current Builder or Reviewer pass executes after the refactor
Then a registered runner adapter owns its provider-specific command flags,
child environment, capabilities, and final-output decoding
And the worker receives one normalized invocation/result shape
And existing command-contract and lifecycle behaviour remain unchanged.

### Scenario: A new runner is a local extension

Given the runner contract and registry already exist
When a later story adds another CLI runner
Then it adds an adapter and catalog/profile registration
And it does not add a runner name check to the worker, executor, run service,
state machine, verdict parser, or close path.

### Scenario: Runner capabilities constrain the profile

Given a runner does not support a requested effort or role mode
When a caller submits that profile
Then the API rejects the incompatible combination clearly before dispatch
And it does not silently drop, reinterpret, or invent provider-specific flags.

### Scenario: Dispatch records identity without credentials

Given a valid profile is dispatched
When the worker claims and completes the pass
Then run events identify the resolved runner, provider, model, and effort
And no credential value is written to a row, event, artifact, command argument,
or worker log.

### Scenario: An unknown profile cannot touch the checkout

Given a run references an unknown or disabled runner/provider/model combination
When dispatch is attempted
Then the attempt fails before an agent process can mutate the repository
And the run reaches the existing visible failure handoff rather than silently
falling back to another provider.

## Scope

- `allowed_paths`:
  - `tickets/backlog/E005-S00-dispatch-resolves-an-explicit-runner-neutral-agent-profile.md`
  - `ARCHITECTURE.md`
  - `apps/api/schema/**`
  - `apps/api/app/main.py`
  - `apps/api/app/features/agent_profiles/**`
  - `apps/api/app/features/runs/models.py`
  - `apps/api/app/features/runs/repository.py`
  - `apps/api/app/features/runs/controller.py`
  - `apps/api/app/services/agent_profiles.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/agent_profiles/**`
  - `apps/api/tests/features/runs/test_agent_profiles.py`
  - `apps/api/tests/features/runs/test_run_providers.py`
  - `packages/domain-types/src/index.ts`
- `read_context_paths`:
  - `apps/api/app/config.py`
  - `tickets/complete/E002-S00-route-shaping-building-and-review-through-explicit-agent-profiles.md`
  - `tickets/backlog/E002-S02-choose-each-run-role-s-agent-model-and-effort.md`
  - `tickets/complete/027-dispatch-agents-at-a-chosen-effort.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/features/discussions/**`
  - `apps/api/app/services/discussion_agent.py`
  - `apps/web/**`
- `depends_on`:
  - `E002-S00`
- `parallelizable`: no — it is the shared persistence and dispatch contract;
  E003-S01 currently owns `worker.py`, while E002-S01 also plans to own schema
  and domain contracts. Those locks must clear before this story is promoted.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [ ] A typed agent profile distinguishes runner, provider, model, and nullable
      effort and declares enough runner capabilities to reject unsupported
      combinations.
- [ ] Claude, Codex, and Stub implement one runner adapter protocol that owns
      command construction, selected environment, capabilities, and output
      normalization.
- [ ] Worker/executor orchestration contains no Claude/Codex/Stub name branches;
      contract tests prove adding a fake registered adapter requires no changes
      to the run lifecycle or common verdict/disposition handling.
- [ ] Builder and Reviewer profile snapshots survive create, retrieve, board,
      fix, review, restart, and one-off dispatch paths.
- [ ] Existing `provider:model` payloads and rows retain today's Claude, Codex,
      and Stub behaviour behind one explicit compatibility path.
- [ ] Dispatch and pass events record the resolved non-secret profile identity;
      tests prove credentials cannot appear in persisted or logged payloads.
- [ ] Invalid or unavailable profiles fail before agent execution and follow
      the existing visible worker-failure semantics without automatic fallback.
- [ ] Current Claude defaults remain unchanged and are pinned by regression
      tests.
- [ ] `make test`, Ruff, TypeScript, and the ticket scope guard pass.

## Non-goals

- Adding Aider, Gemini, DeepSeek, model health checks, latency routing, or
  fallback execution.
- Changing the shaping discussion's Codex profile or session ownership.
- Changing run states, lease ownership, verdict parsing, close behaviour, or
  human approval.
