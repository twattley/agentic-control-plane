# Ticket 010: Optional evidence artifact showing what a run produced

## Summary

Some work has an outcome you should *see*, not infer from a diff. Let a builder
optionally attach one self-contained HTML artifact as **evidence the outcome
happened**, and render it in the run view. Two flavours cover nearly everything:
a rendered preview for visual work, and a demonstrated case table — real inputs
beside real outputs — for data and logic work. Optional by design: a refactor's
truth is its diff, and no run is ever required to produce one.

## Status

- State: ready
- Phase: queued
- Started: —
- Updated: 2026-08-15
- Completed: —
- Last: shaped in conversation; the north star is seeing the outcome, not
  reading the mechanism
- Next: claim builder

## Why

Reviewing a run today means reading a unified diff, on a phone, and mentally
executing it. That is the right artifact for logic changes and the wrong one
for anything visual or data-shaped. The plane already stores artifacts
(`kind`: `diff` | `test_output` | `screenshot` | `log`) and already renders the
diff well, so the gap is one artifact kind and one viewer — not a new subsystem.

## Capability

A builder that judges its work to have a demonstrable outcome writes a single
self-contained HTML file to an agreed path in the checkout. The worker picks it
up after the build pass, attaches it as an `html` artifact, and the run view
renders it inline (sandboxed) beneath the brief, above the diff. A run without
one looks exactly as it does today.

The evidence is drawn from the story's own `## Scenarios` and `## Done When`
sections, so the artifact answers the acceptance criteria that were agreed at
freeze rather than whatever the builder found easy to display:

- **Visual work** — render the thing: the component, page, or chart as it now
  looks.
- **Data or logic work** — demonstrate the cases: a table of concrete inputs,
  expected outputs, and actual outputs, one row per scenario, including the
  edge and failure rows. Real values produced by running the code, never
  hand-written prose claiming it works.

## Public Interface

- Builder prompt gains an optional instruction: if the change has a visual or
  demonstrable outcome, write one self-contained HTML file (no external
  requests) to `.agent-artifacts/<run_id>.html` — a rendered preview for visual
  work, or a case table of real inputs and actual outputs for data/logic work,
  covering the story's scenarios; otherwise write nothing.
- Worker: after the build pass, if that file exists, attach it as
  `ArtifactIn(kind="html", ...)` and delete it from the checkout so it never
  lands in the commit.
- `ArtifactKind` gains `html` (Pydantic + `packages/domain-types`).
- Run view renders the newest `html` artifact in a sandboxed iframe
  (`sandbox` with no `allow-same-origin`), collapsed by default with a
  "Preview" toggle.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/features/runs/models.py`
  - `apps/api/tests/features/runs/**`
  - `apps/web/src/features/runs/**`
  - `packages/domain-types/src/index.ts`
- `read_context_paths`:
  - `ARCHITECTURE.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/schema/**`
- `depends_on`:
  - none
- `parallelizable`: yes

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [ ] A builder pass that writes the artifact file produces an `html` artifact
      on the run; the file does not survive into the commit.
- [ ] A builder pass that writes nothing produces no artifact and no error.
- [ ] The run view renders the artifact sandboxed, and cannot execute
      same-origin script against the plane.
- [ ] Prompt wording makes the artifact genuinely optional — no artifact is
      never treated as a failure by the reviewer.
- [ ] Prompt wording asks for actual outputs from running the code, and the
      reviewer treats a case table of asserted-but-unrun claims as grounds for
      `VERDICT: changes`.
