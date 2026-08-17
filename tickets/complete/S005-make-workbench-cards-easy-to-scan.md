# Make workbench cards easy to scan

## Identity

- `kind`: `story`
- `story_id`: `S005`
- `epic_id`: `none`
- `coordination_class`: `feature`

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 20:14:12 BST
- Updated: 2026-08-17 20:18
- Completed: 2026-08-17 20:18
- Last: owner accepted the direct small-task visual review; web and repository close gates passed
- Next: closed

## Story

The owner can scan active work without ticket metadata crowding out the title.
Each workbench card leads with a compact work number and a fully readable title,
then shows only its state and the age of the latest run event.

## Scenarios

| Case | Workbench card |
|---|---|
| Epic story `E001-S04` | Shows `E001 · S04` without field labels or backticks |
| Standalone story `S004` | Shows `S004` only |
| Long title | Wraps naturally across lines without an ellipsis |
| Card details | Omits the ticket summary; footer contains only the state pill and wording such as `reviewer claimed 5m ago` |

For other latest event types, the same humanized event wording and age format
applies, for example `builder claimed 2m ago`. With no event, only the state
pill appears.

## Scope

- `allowed_paths`:
  - apps/web/src/features/runs/Workbench.tsx
- `read_context_paths`:
  - packages/domain-types/src/index.ts
  - apps/web/src/features/runs/StateBadge.tsx
- `forbidden_paths`:
  - none
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
cd apps/web && npx tsc -b --noEmit && npm run build
```

## Done When

- [x] Epic and standalone story numbers use the agreed compact presentation.
- [x] Long titles wrap without truncation.
- [x] Ticket summaries no longer render in workbench cards.
- [x] The footer contains only the state pill and a humanized latest-event age when available.
- [x] Web typecheck and production build pass.
