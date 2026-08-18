# Choose each run role's agent model and effort

## Identity

- `kind`: `story`
- `story_id`: `E002-S02`
- `epic_id`: `E002`
- `coordination_class`: `contract`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: reshaped against E005 runner-neutral profile contract; Claude stays default through 17 September review
- Next: wait for E005-S00, then add RED profile-picker tests

## Story

Replace each role's combined agent picker with explicit Runner, Provider,
Model, and Effort controls backed by the server's E005-S00 profile catalog.
Builder and Reviewer remain independent, and the form submits the exact
resolved profiles that the run will preserve across fix and review passes.

Keep Claude Sonnet medium and Claude Opus high as the visible defaults through
the owner's 17 September 2026 subscription review. The picker may expose
configured Aider/Gemini and Aider/DeepSeek profiles when their integration is
available, but this story neither installs runners nor changes routing policy.

## Scenarios

### Scenario: The default profile is visible before a run starts

Given the owner opens a new run form
When they have not changed any agent controls
Then Builder shows Claude / Sonnet / Medium
And Reviewer shows Claude / Opus / High
And submitting the form persists those exact choices on the run.

### Scenario: Builder and Reviewer can be configured independently

Given the new run form is open
When the owner selects Codex / OpenAI / GPT-5.6 SOL / High for Builder
And leaves Reviewer as Claude / Anthropic / Opus / High
Then the submitted Builder and Reviewer profiles match those selections
And changing one role never changes the other role's controls.

### Scenario: Runner and provider constrain later choices

Given a role's Runner control is Aider
When the owner chooses Google as Provider
Then only enabled Gemini models and their supported efforts are offered
When the owner changes Provider to DeepSeek
Then an incompatible Gemini model is not retained
And choosing Stub clears Provider, Model, and Effort because none apply.

### Scenario: Only configured runnable profiles are offered

Given the server catalog marks a runner or credential unavailable
When the owner opens the profile picker
Then that combination is absent or visibly unavailable with an actionable
reason
And the UI does not imply that selecting it can start a pass.

### Scenario: Later passes retain the run profile

Given a run stores a builder and reviewer profile
When the builder enters a fix round or the reviewer is dispatched again
Then each detached worker receives that role's stored provider, model, and
effort
And a service restart or later global setting change does not alter the run's
stored profile.

### Scenario: A one-off dispatch does not erase the run profile

Given a run already stores a role effort
When the owner re-runs the stage from its detail page
Then the ordinary stored profile is used
And no hidden UI default or catalog change overwrites it.

## Scope

- `allowed_paths`:
  - `tickets/backlog/E002-S02-choose-each-run-role-s-agent-model-and-effort.md`
  - `apps/web/src/api/hooks.ts`
  - `apps/web/src/features/projects/ProjectView.tsx`
  - `apps/web/src/features/projects/AgentProfilePicker.tsx`
  - `apps/web/src/features/projects/__tests__/**`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `packages/domain-types/src/index.ts`
  - `tickets/complete/027-dispatch-agents-at-a-chosen-effort.md`
  - `tickets/complete/E002-S00-route-shaping-building-and-review-through-explicit-agent-profiles.md`
  - `tickets/backlog/E005-S00-dispatch-resolves-an-explicit-runner-neutral-agent-profile.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/app/**`
  - `apps/api/schema/**`
  - `packages/domain-types/**`
  - `apps/web/src/features/projects/DiscussionPanel.tsx`
- `depends_on`:
  - `E002-S00`
  - `E005-S00`
- `parallelizable`: yes — after E005-S00 lands, this story changes only the web
  profile picker and its tests, so E005-S01 can add the Aider adapter in API
  service/configuration paths at the same time. It still conflicts with
  E002-S01 wherever that story owns `apps/web/src/api/hooks.ts`.

## Validation

```bash
cd apps/web && npm test -- src/features/projects
cd apps/web && npx tsc -b --noEmit && npm run build
```

## Done When

- [ ] Builder and Reviewer each render Runner, Provider, Model, and applicable
      Effort controls from the server catalog, with current Claude defaults.
- [ ] Changing Runner or Provider cannot retain an incompatible hidden Model or
      Effort; Stub submits no stale fields.
- [ ] Unavailable profiles are absent or visibly disabled with the server's
      non-secret readiness reason.
- [ ] Run creation submits each role's exact resolved profile independently,
      and re-running a stage displays and uses the stored profile.
- [ ] Tests cover current defaults, independent role selection, Aider/Gemini,
      Aider/DeepSeek, unavailable profiles, incompatible changes, and Stub.
- [ ] Frontend tests, TypeScript, build, and the ticket scope guard pass.

## Non-goals

- Changing the shaping agent profile or adding provider controls to the
  discussion panel.
- Installing CLIs, accepting credentials, probing provider APIs, or changing
  the Claude service defaults before the subscription review.
- Service-tier/priority selection, arbitrary custom CLI flags, automatic
  fallback policy, or permission-mode controls in the frontend.
- Changing run states, review routing, or profile compatibility semantics.
