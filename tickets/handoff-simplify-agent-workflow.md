# Handoff: Simplify the agent workflow around contracts, T3 Code, and an optional review loop

## Purpose of the next session

Decide and shape the smallest safe transition from the current always-on control-plane ceremony to a lighter, risk-based workflow:

- T3 Code for ordinary interactive dogfooding.
- Small portable task contracts as the default unit of work.
- An explicitly invoked shell-based builder/reviewer loop for AFK or higher-assurance work.
- A deterministic human-approved close/commit/push boundary.

Do not archive or delete the agentic control plane yet. Freezing it while the lighter workflow is dogfooded is reversible; archiving it before the replacement has been exercised is not yet justified by evidence.

## Where the conversation started

Claude performance and latency felt degraded, creating interest in Gemini and DeepSeek and in reducing dependence on any one provider. Aider was considered as a provider-neutral harness. Because the Claude subscription remains paid through 17 September, the near-term intent was to keep using Claude while making future provider substitution possible.

That discussion produced the uncommitted E005 backlog artifacts. Read them rather than recreating their contents:

- `tickets/epics/E005-swap-agent-providers-without-changing-the-workflow.md`
- `tickets/backlog/E005-S00-dispatch-resolves-an-explicit-runner-neutral-agent-profile.md`
- `tickets/backlog/E005-S01-aider-runs-gemini-and-deepseek-builders-without-owning-git-history.md`
- `tickets/backlog/E005-S02-routing-policy-chooses-a-profile-for-each-agent-stage.md`
- `tickets/backlog/E005-S03-fallback-can-retry-only-a-provably-untouched-checkout.md`
- `tickets/backlog/E002-S02-choose-each-run-role-s-agent-model-and-effort.md`

These tickets may now be premature or oversized. Do not implement them until the T3/compact-loop direction has been tested.

## Provider-neutral interface conclusion reached earlier

An interface-design exercise converged on a useful seam if custom runners are still needed:

- A stable agent profile names runner, provider, model, and reasoning effort.
- The workflow calls one agent-pass executor with a bounded pass request.
- A runner adapter translates that request into a prepared invocation.
- A generic process host owns subprocess lifecycle, cancellation, timeouts, secret allowlisting, and log redaction.
- The adapter owns CLI flags, permission/capability translation, credential binding, and output decoding.
- Avoid arbitrary provider-option dictionaries in the workflow domain.
- A fake adapter should prove that swapping runners does not change workflow or state-machine behaviour.

This remains a sound design, but it should only be built if the simpler T3/OpenCode/provider-CLI path leaves a demonstrated gap.

## T3 Code research outcome

T3 Code currently provides a macOS desktop app, local web app, web/mobile clients, local and remote execution, provider CLI integration, persistent sessions, worktrees, terminals, diffs, and Git hosting integration. The transcript's suggestion that there is no Mac app is outdated; the Linux-only part is the persistent systemd background service.

Relevant primary sources:

- <https://github.com/pingdotgg/t3code/blob/main/README.md>
- <https://github.com/pingdotgg/t3code/blob/main/docs/user/install.md>
- <https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md>
- <https://github.com/pingdotgg/t3code/blob/main/docs/internals/overview.md>

T3 overlaps heavily with the ACP UI, remote-control, provider-adapter, session, worktree, and terminal ambitions. It does **not** currently appear to provide the desired black box:

```text
submit frozen work unit
  -> builder implements
  -> independent reviewer judges
  -> findings return to builder
  -> bounded revisions continue until pass
  -> deterministic checks run
  -> human approves landing
```

T3 can host separate interactive builder and reviewer threads, but the user would currently coordinate those threads. No documented stable public orchestration/plugin API was found for ACP to drive this loop. A proposed MCP bridge for external agents to consume T3 review feedback was closed as not planned: <https://github.com/pingdotgg/t3code/issues/345>.

Therefore T3 is currently best treated as a complementary interactive workbench, not as the owner of the builder/reviewer state machine.

## Key realization about quality and ceremony

The independent builder/reviewer bounce has caught real bugs, so it has demonstrated value. The problem is making every change pay for it.

Code quality is driven primarily by:

- A clear observable contract.
- Small vertical slices.
- Explicit positive, negative, edge, unset, and failure cases where relevant.
- Narrow diffs and repository context.
- Proportionate automated checks.
- Human inspection of consequences.

Independent review is additional insurance. It is particularly valuable for unattended work, architecture, migrations, data integrity, authentication, security, broad refactors, surprising diffs, and weakly tested areas. It need not be mandatory for reversible dogfood UI changes, chores, and small well-tested fixes.

The current personal charter contains a tension: it says to optimize personal dogfood for the simplest useful slice and fast feedback, while also imposing the full ticket/builder/reviewer/gate/close chain on all non-trivial work. Moving the heavy chain into an opt-in lane would resolve that tension.

## Proposed three-lane workflow

### 1. Quick dogfood (default)

```text
small contract -> one agent builds -> tests -> self-reviews diff -> human dogfoods
```

No independent reviewer or workflow ledger unless the task earns one.

### 2. Guarded

```text
contract -> builder -> checks -> one independent review -> human decision
```

Use when risk or uncertainty is meaningful but a full autonomous revision loop is unnecessary.

### 3. AFK black box

```text
frozen ticket/contract
  -> builder/reviewer shell loop
  -> deterministic gate
  -> human approval
  -> deterministic close/commit/push
```

This is where the existing builder, reviewer, claim, findings, scope, and close machinery remains valuable.

## Portable micro-contract proposed for ordinary T3 work

```markdown
## Outcome
What should become observably different?

## Done when
- Behavioural result.
- Behaviour that must remain unchanged.

## Cases
| Given | When | Then |
|---|---|---|
| ... | ... | ... |

## Scope
May change:
- ...

Must not change:
- ...

## Verification
- Automated command.
- Manual dogfood check.

## Handoff
Do not commit. Report changed files, checks, and remaining risks.
```

Prefer small complete vertical behaviours over technical fragments split by database/service/API/UI layer.

## Proposed compact builder/reviewer loop

The simplification under consideration is a small shell orchestrator rather than a large control-plane application:

```text
for at most N rounds:
    invoke a fresh builder session with contract + latest findings
    enforce changed-file scope
    run deterministic tests
    invoke a fresh read-only reviewer with contract + diff + test evidence
    if structured verdict passes: stop ready_for_human
    otherwise persist findings for the next builder round

on exhaustion, malformed output, provider failure, or ambiguity:
    stop needs_human
```

Required invariants:

- Never use an unbounded `while not pass` loop.
- Use fresh agent contexts for each role/pass.
- Communicate through files and structured artifacts, not accumulated conversations.
- Builder may edit only declared paths.
- Reviewer is read-only and does not fix its own findings.
- Prefer different model families for builder and reviewer when available.
- Run the scope guard after every builder pass.
- Do not invoke review until deterministic checks pass, unless reviewing the failure itself is explicitly intended.
- Validate reviewer output against a schema.
- Agents never stage, commit, or push.
- Human approval is required before a deterministic closer stages exact files, reruns gates, commits, and optionally pushes.

## Do we need another agent or skill?

The builder and reviewer roles remain. A third reasoning agent is not inherently required to operate the loop; the shell script should be the deterministic orchestrator.

A small opt-in skill or command may still be useful as the human entry point. Its job would be to:

- Confirm/freeze the work contract.
- Select the AFK lane explicitly.
- Launch the shell loop.
- Surface the final pass, needs-human condition, or infrastructure failure.

It should not reimplement orchestration in prose or make every task route through builder/reviewer. Existing builder/reviewer skills and file-based findings can remain behind that command if they fit the compact design.

The `agentic-engineering` repository should evolve from mandatory constitution toward a toolbox: contracts and coding safety always available; guarded review and AFK orchestration invoked when earned.

## Current recommendation

1. Do not archive ACP yet; freeze feature expansion.
2. Dogfood T3 on approximately five real low-risk tasks using portable micro-contracts.
3. Record which global instructions help, which create friction, and what bugs self-review misses.
4. In parallel or afterward, shape the minimal shell-loop contract using existing portable ledger and closer machinery where it genuinely reduces work.
5. Only then decide whether ACP becomes archived, a thin work-board/audit projection, or remains the UI for the AFK lane.
6. Reassess E005 after observing whether T3/OpenCode and existing subscription-backed provider CLIs already provide enough model flexibility.

## Dirty-worktree warning

At handoff time, the E005 artifacts listed above are untracked and `tickets/backlog/E002-S02-choose-each-run-role-s-agent-model-and-effort.md` is modified. Treat these as existing user/conversation work. Do not discard, overwrite, commit, or implement them without first deciding how they relate to the simplified direction.

## Suggested skills

- `shape-feature`: shape the lightweight three-lane workflow and isolate its first vertical slice.
- `agentic-coding`: define ticket boundaries, paths, conflicts, and validation if implementation is authorized.
- `grill-to-tests`: turn the shell orchestrator behaviour into an observable contract and RED cases before implementation.
- `design-an-interface`: use only if the runner boundary still needs exploration after T3 dogfooding; one interface exercise has already been completed conceptually.
- `write-a-skill`: create the opt-in AFK entry-point skill only after the shell-loop contract is stable.
- `coding-standards`: load before implementing or reviewing the shell runner.

## First question for the next session

Which experiment should be shaped first: the five-task T3 dogfood trial, or the minimal bounded shell builder/reviewer loop? The recommended order is the T3 trial first because it is cheaper and may change the requirements of the loop.
