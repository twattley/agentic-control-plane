# Ticket 010: Optional evidence artifact showing what a run produced

## Summary

Some work has an outcome you should *see*, not infer from a diff. Let a builder
optionally attach one **markdown** evidence artifact — a demonstrated case
table of real inputs and actual outputs — and render it in the run view with
the renderer the app already ships. Optional by design: a refactor's truth is
its diff, and no run is ever required to produce one.

Markdown, not HTML, on purpose: agents write it natively, it stays reviewable
in a terminal and a git diff, it renders consistently with every other document
in the app, and it removes the entire surface of executing agent-authored
markup inside the control plane.

## Status

- State: complete
- Phase: closed
- Started: 2026-08-15 13:36 BST
- Updated: 2026-08-15 14:31 BST
- Completed: 2026-08-15 14:31 BST
- Last: 2026-08-15 14:31 BST - human closed on a green gate: 126 pytest, tsc
  clean, ruff clean on all changed files
- Next: none

## Closing Note

Closed by human decision with the last recorded reviewer verdict at
needs-work. That verdict was about documentation being as-built, and the
builder pass at 14:24 made the changes it asked for; no reviewer pass ran
afterwards to record the pass. The functional work was settled two rounds
earlier.

Four files landed outside `allowed_paths` — `apps/api/schema/001_init.sql`
(which this ticket lists as forbidden), `ARCHITECTURE.md` (read-context),
`apps/web/src/features/projects/DocumentBody.tsx`, and the web
`package.json`/lockfile for `remark-gfm`. All are comment-only edits except
the GFM dependency, which the table rendering genuinely needed. Accepted
knowingly rather than overlooked.

Two process gaps this ticket exposed, both worth their own story:

1. The reviewer demanded a change to a read-context file, so the component
   enforcing the scope contract instructed a breach of it.
2. `max_review_rounds` (2) would have escalated the fourth round to a human,
   but it only fires on worker-dispatched passes; these were manual `$reviewer`
   calls from the CLI and bypassed it.

## Why

Reviewing a run today means reading a unified diff, on a phone, and mentally
executing it. That is the right artifact for logic changes and the wrong one
for anything visual or data-shaped. The plane already stores artifacts
(`kind`: `diff` | `test_output` | `screenshot` | `log`) and already renders the
diff well, so the gap is one artifact kind and one viewer — not a new subsystem.

## Capability

A builder that judges its work to have a demonstrable outcome writes a single
markdown file to an agreed path in the checkout. The worker picks it up after
the build pass, attaches it as an `evidence` artifact, and the run view renders
it beneath the brief, above the diff. A run without one looks exactly as it
does today.

The evidence is drawn from the story's own `## Scenarios` and `## Done When`
sections, so the artifact answers the acceptance criteria that were agreed at
freeze rather than whatever the builder found easy to display:

- **Data or logic work** — demonstrate the cases: a markdown table of concrete
  inputs, expected outputs, and actual outputs, one row per scenario, including
  the edge and failure rows. Real values produced by running the code, never
  prose claiming it works.
- **Visual work** — describe what to look at and paste the observed output
  (rendered text, key values, a screenshot artifact if one exists). A live
  rendered preview is explicitly out of scope for this ticket.

## Public Interface

- Builder prompt gains an optional instruction: if the change has a
  demonstrable outcome, write one markdown file to
  `.agent-artifacts/<run_id>.md` — a case table of real inputs and actual
  outputs covering the story's scenarios; otherwise write nothing.
- Worker: after the build pass, if that file exists, attach it as
  `ArtifactIn(kind="evidence", ...)` and delete it from the checkout so it
  never lands in the commit.
- `ArtifactKind` gains `evidence` (Pydantic + `packages/domain-types`).
- Run view renders the newest `evidence` artifact with the existing
  `DocumentBody` renderer, above the diff.

## Scope

- `allowed_paths`:
  - `ARCHITECTURE.md`
  - `apps/api/app/worker.py`
  - `apps/api/app/features/runs/models.py`
  - `apps/api/schema/001_init.sql`
  - `apps/api/tests/features/runs/**`
  - `apps/web/package.json`
  - `apps/web/src/features/projects/DocumentBody.tsx`
  - `apps/web/src/features/runs/**`
  - `package-lock.json`
  - `packages/domain-types/src/index.ts`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`:
  - none
- `parallelizable`: yes

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [ ] A builder pass that writes the artifact file produces an `evidence`
      artifact on the run; the file does not survive into the commit.
- [ ] A builder pass that writes nothing produces no artifact and no error.
- [ ] The run view renders the evidence above the diff using the existing
      markdown renderer — no raw HTML from an agent is ever executed.
- [ ] Prompt wording makes the artifact genuinely optional — no artifact is
      never treated as a failure by the reviewer.
- [ ] Prompt wording asks for actual outputs from running the code, and the
      reviewer treats a case table of asserted-but-unrun claims as grounds for
      `VERDICT: changes`.
