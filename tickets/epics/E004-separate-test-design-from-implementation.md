# Separate test design from implementation

## Identity

- `kind`: `epic`
- `epic_id`: `E004`

## Outcome

Tom can choose an opt-in build loop where one agent owns the executable RED
contract, a second agent implements against that frozen contract, and a third
reviews the result. The control plane makes each handoff and its evidence
visible instead of asking one general-purpose builder to specify and satisfy
its own work.

## Done When

- [ ] A split-mode run moves through test-author, implementer, reviewer, human,
      and deterministic close without conflating their responsibilities.
- [ ] The implementer cannot silently rewrite the RED contract it received.
- [ ] The workbench shows the contract, implementation, review, and current
      owner clearly enough for Tom to QA the loop.

## Stories

- `E004-S00`
- `E004-S01`
- `E004-S02`

## Boundaries

- Split mode is opt-in; existing direct and TDD builder/reviewer runs keep
  their current lifecycle.
- The portable role and ledger contract is authored and landed in
  `agentic-engineering` before this repo depends on it.
- Close remains a deterministic system operation, not a fourth agent role.

## Non-goals

- Multi-user assignment, approvals, or permissions.
- Automatically deciding which product behavior the tests should specify.
- Replacing independent human review with generated evidence.
