# A run must never stage or commit changes outside its ticket boundary

## Identity

- `kind`: `story`
- `story_id`: `S004`
- `epic_id`: `none`
- `coordination_class`: `platform`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: found dogfooding football run 6 (E001-S06); a forbidden-path change carrying a live secret was staged at awaiting_human
- Next: prioritise, then RED-first the boundary guard at stage/commit time

## Story

A run can reach `awaiting_human` with a change to a file in the ticket's
`forbidden_paths` **staged for commit**, so a single human approve would commit
work outside the ticket's declared boundary — including secrets. The reviewer's
narrative cannot be trusted to prevent this: it claimed the file was unstaged
while `git` showed it staged, and a later builder cycle re-staged it.

Observed on `football-api-project` run 6, ticket `E001-S06`:

- `schema/seeds/2026-27-target-clubs.json` is in S06's `forbidden_paths` (it is
  Tom's data via `forum_research.py`, not builder output), yet it was **staged**
  in the run's diff at `awaiting_human`.
- That staged row carried a **live phpBB `sid=` session token** — approving the
  run would have committed a secret into history.
- The reviewer's own findings asserted *"unstaged it for real this time"* — but
  `git diff --cached` still showed the token staged. The review text described a
  mitigation the repository state contradicted.

Two failures compound here: (1) nothing enforces the ticket's own
`allowed_paths` / `forbidden_paths` at stage/commit time, and (2) an agent's
prose claim about repo state is taken at face value instead of being checked.
Boundary enforcement is the durable fix — it does not depend on any agent
telling the truth.

## Scenarios

### Scenario: The closer refuses a commit touching a forbidden path

Given a run whose staged diff includes a file inside the ticket's `forbidden_paths`
When the human approves and the closer runs
Then the close fails with a clear boundary error naming the offending path
And nothing is committed.

### Scenario: The closer commits only allowed paths

Given a run whose working tree also has incidental changes outside `allowed_paths`
When the closer commits
Then only paths inside `allowed_paths` are staged and committed
And out-of-boundary changes are left in the working tree, untouched.

### Scenario: A secret never rides in on approve (should not happen)

Given a forbidden-path change that contains a secret (e.g. a session token)
When the run sits at `awaiting_human` and is approved
Then that change must NOT be committed
And the human must not have to notice it manually to prevent the leak.

## Scope

- `allowed_paths`:
  - apps/api/app/worker.py
  - apps/api/tests/features/runs/
- `read_context_paths`:
  - apps/api/app/services/executor.py
  - ARCHITECTURE.md
- `forbidden_paths`:
  - none
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
make test
```

A RED-first test that drives a run whose staged diff includes a
`forbidden_paths` file and asserts the closer refuses to commit it; plus a test
that incidental out-of-`allowed_paths` changes are left uncommitted.

## Done When

- [ ] The closer stages/commits only paths inside the ticket's `allowed_paths`.
- [ ] A change touching a `forbidden_paths` file fails the close with a clear, path-naming error and commits nothing.
- [ ] Enforcement is structural (at stage/commit time), independent of any reviewer's prose claims.
- [ ] Covered by RED-first tests; `make test` green.
