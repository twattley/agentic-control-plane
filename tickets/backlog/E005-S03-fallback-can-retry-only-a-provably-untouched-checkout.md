# Fallback can retry only a provably untouched checkout

## Identity

- `kind`: `story`
- `story_id`: `E005-S03`
- `epic_id`: `E005`
- `coordination_class`: `validation`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: portable writer created E005-S03
- Next: hold behind E005-S02; define failure classes from real Aider dogfood

## Story

Allow an ordered routing policy to try its next ready profile after a bounded,
classified provider failure only when the control plane proves the failed
attempt left the candidate checkout unchanged. Every fallback starts a new
one-shot runner context grounded from the frozen ticket, current run evidence,
and exact checkout state; it never resumes or forwards the failed provider's
conversation history.

If a failed attempt may have edited, staged, cleaned, reset, or committed
anything, stop automatic routing and expose the partial candidate to the human.
Protecting irreplaceable work is more important than hiding provider latency.

## Scenarios

### Scenario: Preflight failure safely advances policy

Given the first policy profile fails readiness before process launch
When another ready profile remains
Then dispatch records the classified failure and selects the next profile
And no checkout comparison or cleanup is needed because no agent started.

### Scenario: A started but untouched pass may retry cleanly

Given a provider process started and returned a recognized transient failure
And the checkout HEAD, index, worktree, and relevant untracked set exactly match
the baseline captured before that attempt
When another ready policy profile remains
Then the failed lease/attempt is finalized once
And a fresh one-shot context is built from canonical ticket/run/checkout facts
And the next profile gets one bounded attempt.

### Scenario: A possibly mutated checkout stops fallback

Given a failed or timed-out provider attempt changed HEAD, the index, the
worktree, or relevant untracked files
When fallback eligibility is evaluated
Then no second model process is launched
And the run records the partial checkout mark, diff/evidence available, failed
profile, and reason
And the existing human failure surface explains that automatic retry was
refused to preserve the candidate.

### Scenario: Fallback cannot loop indefinitely

Given a role policy contains several profiles
When failures advance through the policy
Then each resolved profile is attempted at most once for that dispatch cycle
And the bounded attempt history is recorded
And exhausting the policy reaches the existing visible human handoff.

### Scenario: Unknown failure text is not guessed into a retry

Given a runner exits unsuccessfully without a recognized adapter-level failure
classification
When fallback eligibility is evaluated
Then the failure is treated as unsafe to retry automatically
And arbitrary stderr wording is not used as proof of a rate limit or clean
provider outage.

## Scope

- `allowed_paths`:
  - `tickets/backlog/E005-S03-fallback-can-retry-only-a-provably-untouched-checkout.md`
  - `ARCHITECTURE.md`
  - `apps/api/app/services/agent_profiles.py`
  - `apps/api/app/services/agent_runners/**`
  - `apps/api/app/services/routing_policy.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/agent_profiles/test_fallback.py`
  - `apps/api/tests/features/runs/test_agent_pass_failure.py`
  - `apps/api/tests/features/runs/test_external_edits.py`
- `read_context_paths`:
  - `apps/api/app/services/runs_service.py`
  - `apps/api/app/services/state_machine.py`
  - `tickets/complete/023-a-crashed-agent-pass-must-not-strand-the-run.md`
  - `tickets/complete/029-edits-from-outside-the-run-must-not-be-silently-absorbed.md`
  - `tickets/backlog/E005-S02-routing-policy-chooses-a-profile-for-each-agent-stage.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/features/discussions/**`
  - `apps/api/schema/**`
  - `packages/domain-types/**`
  - `apps/web/**`
- `depends_on`:
  - `E005-S02`
- `parallelizable`: no — fallback coordinates the runner adapter, routing
  policy, worker failure guard, checkout marks, and run events as one safety
  invariant.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] Runner adapters return a closed, tested failure classification instead of
      routing from arbitrary stderr substrings.
- [ ] Preflight failures may advance policy without launching a process;
      started attempts may advance only after an exact unchanged-checkout proof.
- [ ] Any possible checkout mutation refuses automatic fallback and preserves
      partial diff/evidence for the existing human failure handoff.
- [ ] A dispatch cycle attempts each resolved profile at most once and records
      bounded non-secret attempt/selection history.
- [ ] Every retry uses canonical ticket, run, artifact, git-status, and diff
      facts in a new runner process without failed conversation history.
- [ ] Tests cover missing binary/key, classified transient failure, timeout,
      unknown exit, staged/unstaged/untracked edits, moved HEAD, clean retry,
      policy exhaustion, and duplicate dispatch races.
- [ ] `make test`, Ruff, and the ticket scope guard pass.

## Non-goals

- Cleaning, resetting, stashing, or otherwise repairing a failed provider's
  checkout automatically.
- TTFT thresholds or repetitive-tool-call detection before runner output is
  durably streamed with trustworthy lifecycle telemetry.
- Retrying validation/close-gate failures through a different model.
- Changing run states, lease semantics, or the human approval boundary.
