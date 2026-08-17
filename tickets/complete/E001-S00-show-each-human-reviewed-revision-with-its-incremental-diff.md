# Show each human-reviewed revision with its incremental diff

## Identity

- `kind`: `story`
- `story_id`: `E001-S00`
- `epic_id`: `E001`
- `coordination_class`: `feature`

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 09:32:34 BST
- Updated: 2026-08-17 10:17
- Completed: 2026-08-17 10:17
- Last: close-ticket verified reviewer run d9ce84410ba90c23 and close gate passed
- Next: closed

## Story

When an agent loop returns work to the human, append one human-visible revision
to the run detail page: a deliberate one-sentence summary and the reviewed code
diff. The initial revision shows the whole ticket change. If the human requests
changes, show that request as the boundary and append the next reviewed result
below it with only the code changed since that request. Keep prior revisions in
place so scrolling down tells the chronological story of the conversation and
the code.

The builder/reviewer loop may bounce several times inside a revision. Those
rounds still keep their events, cumulative diffs, findings, and evidence for
the agents and diagnostics, but none becomes a human-visible revision until the
run returns to `awaiting_human`. A normal informational note is not a revision
boundary; only the human's `request_changes` decision is.

## Scenarios

### Scenario: Initial agent loop returns its reviewed implementation

Given a new run whose builder and reviewer may complete several internal rounds
When a reviewer pass or exhausted-round escalation returns the run to the human
Then the page shows one checkpoint with a one-sentence summary and the final
reviewed diff from the run's starting Git state
And it shows no intermediate builder briefs, reviewer findings, evidence, or
diffs from the private rounds.

### Scenario: Human-requested work returns as an incremental revision

Given the initial reviewed checkpoint is visible
When the human requests "add three loading dots"
And the next private agent loop returns to the human
Then the request appears below the initial checkpoint
And a second checkpoint appears below the request
And its diff contains only changes made since the request-change boundary, not
the initial implementation repeated.

### Scenario: Several requests tell a chronological story

Given the human requests changes more than once
When each private agent loop returns a reviewed result
Then each request and response checkpoint is appended below the previous one
in oldest-to-newest order
And every response diff is relative to the immediately preceding human
checkpoint.

### Scenario: A private review bounce stays private

Given the reviewer requests agent changes before the run reaches the human
When another builder pass attaches a cumulative diff and another reviewer pass
runs
Then no extra human-visible section appears for either pass
And the reviewer continues to receive the full current candidate diff needed
to review correctness.

### Scenario: An informational note is not a request-change boundary

Given the run has a human-visible checkpoint
When the human adds a note without choosing Changes
Then the note does not establish a new diff baseline or create an empty
revision section.

### Scenario: Older run has no persisted revision checkpoints

Given a run predates this capability
When its detail page opens
Then it shows one current summary and current diff using the existing fallback
And it does not fabricate an incremental history from ambiguous old events.

## Scope

- `allowed_paths`:
  - `tickets/epics/E001-see-code-evolve-through-human-review.md`
  - `apps/api/app/worker.py`
  - `apps/api/app/services/runs_service.py`
  - `apps/api/app/features/runs/**`
  - `apps/api/schema/**`
  - `apps/api/tests/features/runs/**`
  - `packages/domain-types/src/index.ts`
  - `apps/web/src/features/runs/**`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `apps/api/app/services/state_machine.py`
  - `tickets/in-progress/020-reviewer-findings-must-name-a-location-and-a-fix.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/web/src/features/projects/**`
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
make test
uv run --project apps/api ruff check apps/api
cd apps/web && npx tsc -b --noEmit && npm run build
```

## Done When

- [x] A persisted human-review checkpoint records a deliberate one-sentence
      builder summary and a diff baseline that survives worker/API restarts.
- [x] The initial checkpoint exposes the complete reviewed ticket diff; each
      checkpoint after `request_changes` exposes only the delta since the prior
      human checkpoint.
- [x] The reviewer still receives the complete current candidate diff, so the
      human projection does not weaken private review.
- [x] `request_changes` is distinguishable from an informational human note and
      is the only human action that starts a new revision baseline.
- [x] Run detail renders checkpoints and request text chronologically from top
      to bottom, retaining every earlier checkpoint as later revisions arrive.
- [x] Internal builder briefs, findings, evidence, and intermediate diff
      artifacts are not rendered as human-visible checkpoints.
- [x] A pre-capability run falls back to one latest summary and latest diff
      without an error or invented revision history.
- [x] Projection tests cover initial, internal-bounce, first-request,
      repeated-request, informational-note, and legacy-run cases.

## Non-goals

- Reconstructing exact incremental revisions for historical runs that never
  recorded a baseline.
- Changing the run state machine or removing internal events/artifacts.
- Adding this thread to inbox, project, or mobile views.
