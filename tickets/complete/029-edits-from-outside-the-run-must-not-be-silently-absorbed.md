# Ticket 029: Edits from outside the run must not be silently absorbed

## Summary

A plane run executes in a live checkout the owner can also touch from a
terminal pane. acp-022 catches one direction of the crossover — the builder
committing during its own pass — but nothing catches the reverse: a human or
another session editing or committing in the checkout *between* passes while
a run is active. The next pass then diffs against a tree the run's own agents
never produced: the reviewer reviews outside work as if the builder wrote it,
the revision artifacts misattribute it, and the close gate signs it all as
the run's output. Crossing lanes mid-run is currently a workflow rule with no
witness.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 12:04:43 BST
- Updated: 2026-08-17 12:25
- Completed: 2026-08-17 12:25
- Last: close-ticket verified reviewer run 53b334711d7475fc and close gate passed (non-independent review accepted by human)
  verdict pass.
- Next: closed

## Why

The two-lane workflow (UI runs and terminal panes, interchangeable per
ticket) is only safe if crossing lanes *mid-run* is visible. The clean
version — pause or finish the run, then take the ticket over in the
terminal — stays the rule; this ticket makes the unclean version leave a
mark instead of vanishing into the next diff. Detection, not prevention: the
owner editing their own checkout is legitimate, sometimes deliberate. What
must not happen is the run absorbing that work without anyone being told.

## Capability

Each pass ends with the worker recording where it left the tree; each
subsequent pass begins by comparing. When the tree at pass start differs from
where the previous pass left it, the worker records an informational
`external_edits_detected` event before the agent runs — carrying the
before/after heads and a summary saying the checkout changed between passes
by hands outside this run, so the coming diff includes work no agent of this
run did. The run's state does not change (unmapped event types are
informational in the state machine, same as `builder_committed`), the pass
proceeds, and the reviewer and the human both have the fact on the record. A
run whose checkout is undisturbed between passes records nothing new.

## Public Interface

- `apps/api/app/worker.py`: persist the end-of-pass tree mark (the existing
  seams already do the work — `_git_head` for committed movement, the
  `git write-tree` approach in `_revision_base_content` for uncommitted
  movement; an artifact or event payload on the run is the natural place to
  keep the mark, mirroring how `revision_base` already rides the run).
- New informational event type `external_edits_detected`, payload shaped like
  `builder_committed`: `head_before`, `head_after`, `summary`.
- No state machine change: the event maps to no transition, deliberately.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`: none
- `parallelizable`: no — shares `apps/api/app/worker.py` with ticket 027.
  No logical dependency; claim whichever first, rebase the other.

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
uv run --project apps/api ruff check apps/api
```

## Done When

- [ ] A run whose checkout is mutated between two passes (a commit landing,
      or working-tree edits) records exactly one `external_edits_detected`
      event before the second pass's agent output, with differing marks in
      the payload.
- [ ] A run left undisturbed between passes records no such event.
- [ ] The run's state is identical with and without the event — it informs,
      it never transitions.
- [ ] The first pass of a run never fires the event (there is no previous
      pass to differ from).

## Non-goals

- Blocking or pausing the run when outside edits are detected — detection
  only; the human decides what it means.
- Attributing *which* outside actor made the edits.
- Rendering the event in the web UI — acp-026 is building the visible-warning
  surface for `builder_committed`; this event should ride the same pattern,
  and extending that surface is a one-line follow-up once both land.
