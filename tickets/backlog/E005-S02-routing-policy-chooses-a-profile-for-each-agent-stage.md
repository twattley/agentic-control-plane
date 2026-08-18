# Routing policy chooses a profile for each agent stage

## Identity

- `kind`: `story`
- `story_id`: `E005-S02`
- `epic_id`: `E005`
- `coordination_class`: `feature`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-18
- Completed: —
- Last: portable writer created E005-S02
- Next: revisit policy after Aider dogfood and the 17 September subscription decision

## Story

Represent Builder and Reviewer defaults as an explicit ordered routing policy
over resolved agent profiles, rather than provider-specific branches or prose
inside an orchestrator prompt. A run's explicit stored role profile always wins;
otherwise dispatch selects the first enabled, ready profile for that role and
records why it was selected.

Land this only after Aider dogfood gives the owner real evidence. Until an
explicit decision on or after 17 September 2026, the policy's first Builder and
Reviewer choices remain Claude Sonnet medium and Claude Opus high.

## Scenarios

### Scenario: Current defaults are policy entries

Given a new run has no explicit Builder or Reviewer profile
When each role is dispatched before the subscription review decision
Then Builder resolves to Claude Sonnet medium
And Reviewer resolves to Claude Opus high
And the event records the policy entry and resolved profile used.

### Scenario: A per-run choice beats routing policy

Given a run stores an explicit enabled profile for one role
When that role is dispatched or re-dispatched
Then the stored profile is used even if the service policy has changed
And the other role continues to resolve independently.

### Scenario: Policy skips a profile that is not ready

Given an ordered role policy contains a profile whose runner or credential is
unavailable followed by a ready profile
When a run without an explicit choice is dispatched
Then the first ready profile is selected
And the skipped profile and bounded non-secret reason are recorded
And no agent process is started for the skipped entry.

### Scenario: Review remains independent

Given the resolved Reviewer profile is identical to the profile that authored
the current candidate
When the review stage is routed
Then policy selects the next ready independent Reviewer profile
Or, if none exists, the run reaches a visible human handoff instead of allowing
the author profile to approve its own work.

### Scenario: Routing does not guess task complexity

Given a ticket has no explicit standard/deep routing classification
When Builder routing runs
Then policy uses its ordinary Builder order
And does not infer complexity from title wording, token count, or a model's
self-assessment.

## Scope

- `allowed_paths`:
  - `tickets/backlog/E005-S02-routing-policy-chooses-a-profile-for-each-agent-stage.md`
  - `ARCHITECTURE.md`
  - `apps/api/app/config.py`
  - `apps/api/app/services/agent_profiles.py`
  - `apps/api/app/services/routing_policy.py`
  - `apps/api/app/services/executor.py`
  - `apps/api/app/features/runs/models.py`
  - `apps/api/app/features/runs/repository.py`
  - `apps/api/app/features/runs/controller.py`
  - `apps/api/tests/features/agent_profiles/test_routing_policy.py`
  - `apps/api/tests/features/runs/test_dispatch.py`
- `read_context_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/services/state_machine.py`
  - `tickets/complete/022-a-builder-must-not-author-the-verdict-that-closes-its-ticket.md`
  - `tickets/complete/E002-S00-route-shaping-building-and-review-through-explicit-agent-profiles.md`
  - `tickets/backlog/E005-S00-dispatch-resolves-an-explicit-runner-neutral-agent-profile.md`
  - `tickets/backlog/E005-S01-aider-runs-gemini-and-deepseek-builders-without-owning-git-history.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/features/discussions/**`
  - `apps/api/schema/**`
  - `packages/domain-types/**`
  - `apps/web/**`
- `depends_on`:
  - `E005-S00`
  - `E005-S01`
- `parallelizable`: no — it integrates policy with the shared profile resolver,
  dispatch service, and run events after the Aider adapter has produced real
  dogfood evidence.

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] Configuration expresses an ordered list of profile identities for each
      dispatched role; no model ranking or identifier is embedded in prompts.
- [ ] Explicit stored run profiles override policy and remain stable across
      restarts, fix rounds, reviews, and one-off re-dispatch.
- [ ] Readiness filtering happens before process launch and records bounded
      non-secret selection/skipping reasons in run events.
- [ ] Reviewer routing refuses the candidate-authoring profile and chooses an
      independent ready profile or hands off visibly to the human.
- [ ] Regression tests keep Claude first for both roles until an explicit owner
      change after the documented subscription review.
- [ ] `make test`, Ruff, and the ticket scope guard pass.

## Non-goals

- Automatically classifying tickets as standard/deep, estimating context
  tokens, or choosing models from benchmark/pricing data.
- Routing the separate shaping-discussion lifecycle.
- Retrying a failed pass after a provider process has started.
- Changing run states, review verdicts, or the repository close gate.
