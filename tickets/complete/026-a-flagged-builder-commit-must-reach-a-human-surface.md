# Ticket 026: A flagged builder commit must reach a human surface

## Summary

`022` records a `builder_committed` event when a builder pass moves HEAD —
but the run detail page renders revisions, the pending request, and the close
gate, not a generic event timeline, and the board's `last_event` is
overwritten by the builder brief microseconds later. So today the flag is
visible only to someone reading the run's API response raw. A rogue pass
would be recorded and still unseen — which is most of the way back to
silently absorbed.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 11:21:14 BST
- Updated: 2026-08-17 11:30
- Completed: 2026-08-17 11:30
- Last: close-ticket verified reviewer run dc0ed74b2c6061b1 and close gate passed
- Next: closed

## Capability

A run carrying a `builder_committed` event shows it on the run detail page as
a warning the eye cannot miss — placed with the run's other prominent facts
(state badge, close gate), not buried in history. The wording carries the
event's own summary: the builder committed during its pass, the boundary
stops at the handoff.

## Scope

- `allowed_paths`:
  - `apps/web/src/features/runs/**`
- `forbidden_paths`:
  - `apps/api/**`
- `depends_on`:
  - `022-a-builder-must-not-author-the-verdict-that-closes-its-ticket`
- `parallelizable`: yes

## Validation

```bash
cd apps/web && npx tsc -b --noEmit && npm run build
```

## Done When

- [x] A run with a `builder_committed` event shows a visible warning on its
      detail page; a run without one shows nothing new.
- [x] No backend change.
