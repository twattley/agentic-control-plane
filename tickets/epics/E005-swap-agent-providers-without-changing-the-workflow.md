# Swap agent providers without changing the workflow

## Identity

- `kind`: `epic`
- `epic_id`: `E005`

## Outcome

The owner can choose a coding-agent runner, model provider, model, and supported
reasoning effort without changing the control plane's ticket, lock, review, or
close semantics. First, today's Claude, Codex, and Stub execution moves behind
one runner-neutral adapter boundary without changing which agents are selected
or how they behave. Claude remains the paid dogfood default through the owner's
17 September 2026 subscription review; only later stories add Aider-backed
Gemini and DeepSeek profiles behind that already-proven boundary.

## Done When

- [ ] Runs persist a resolved agent profile that distinguishes runner,
      provider, model, and supported effort instead of treating one
      `provider:model` string as all four concepts.
- [ ] Dispatch invokes runners through one tested adapter contract and records
      the resolved profile used for each pass without exposing credentials.
- [ ] Claude, Codex, and Stub use that same contract; adding a runner no longer
      requires another provider-name branch in the worker or run lifecycle.
- [ ] Aider can execute a one-shot builder pass with either Gemini or DeepSeek
      while the control plane proves the builder did not commit.
- [ ] The run form offers only configured, runnable profiles and preserves
      independent Builder and Reviewer choices across later passes.
- [ ] Existing Codex and Claude profiles remain compatible, and no story in
      this epic changes the default away from Claude before an explicit owner
      decision on or after 17 September 2026.

## Boundaries

- The control plane continues to delegate coding to local CLI runners; it does
  not become a home-grown model tool loop or hosted execution service.
- Credentials come from the control-plane environment, are passed only to the
  selected runner/provider process, and never enter database rows, events,
  artifacts, command arguments, or logs.
- Contract work lands before runner and UI integrations. After that contract,
  adapter and presentation stories may run in parallel only where their write
  boundaries do not overlap.
- Automatic failover after a builder may have edited the checkout is deferred
  until the plane can prove whether the failed attempt mutated the candidate.

## Non-goals

- Replacing Claude as the dogfood default before the subscription review.
- Encoding volatile model rankings, prices, or exact fallback policy in an
  orchestrator prompt.
- Supporting arbitrary remote execution, multi-tenant credential storage, or
  every model exposed by every provider.
- Changing the run state machine, review verdict contract, repository close
  gate, or human approval boundary.

## Stories

- `E005-S00`
- `E005-S01`
- `E005-S02`
- `E005-S03`
