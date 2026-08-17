# Remove the unused mobile application

## Identity

- `kind`: `story`
- `story_id`: `S001`
- `epic_id`: `none`
- `coordination_class`: `platform`

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 13:51:55 BST
- Updated: 2026-08-17 14:05
- Completed: 2026-08-17 14:05
- Last: close-ticket verified reviewer run 88877b1a761f0080 and close gate passed
- Next: closed

## Story

Remove the unused Expo/React Native client and every repository-level hook that
installs, runs, or documents it. The owner keeps the responsive web interface
as the only product surface, reducing dependency weight and maintenance noise
without changing API or web behaviour.

## Scenarios

### Scenario: Install the supported monorepo

Given the mobile workspace and its Expo dependencies have been removed
When dependencies are installed from the repository root
Then only the web client and shared packages participate in the npm workspace
And the lockfile contains no mobile workspace or mobile-only dependency graph.

### Scenario: Follow repository guidance

Given a developer opens the root readme, agent guide, architecture document,
or shared-types documentation
When they inspect the supported clients and commands
Then those documents consistently describe the browser interface as the only
client
And no root command offers to start Expo or a native application.

### Scenario: Validate the remaining application

Given the native client has been deleted
When the repository test, lint, and web typecheck commands run
Then the API, web client, and shared types still pass unchanged.

## Scope

- `allowed_paths`:
  - `apps/mobile/**`
  - `package.json`
  - `package-lock.json`
  - `./Makefile`
  - `README.md`
  - `CLAUDE.md`
  - `ARCHITECTURE.md`
  - `packages/domain-types/README.md`
- `read_context_paths`:
  - `apps/web/**`
  - `apps/api/**`
  - `packages/domain-types/src/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/schema/**`
  - `apps/api/app/features/**`
  - `apps/web/src/**`
  - `packages/domain-types/src/**`
- `depends_on`:
  - none
- `parallelizable`: yes — the deletion and root metadata boundary does not
  overlap the active worker ticket's implementation files.

## Validation

```bash
test ! -d apps/mobile
npm install --package-lock-only --ignore-scripts
git diff --check
make test
uv run --project apps/api ruff check apps/api
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [x] `apps/mobile/` is deleted in full; no placeholder native client remains.
- [x] The root npm workspace, scripts, and lockfile contain no
      `@agentic-control-plane/mobile`, Expo, React Native, or React Navigation
      entries that existed solely for the deleted app.
- [x] The root Makefile exposes no mobile target and its `.PHONY` declaration
      matches the remaining commands.
- [x] Root and architecture/developer documentation no longer describe a
      native app, Expo command, or shared-type consumer that does not exist.
- [x] The repository test command, API lint, web typecheck, and lockfile
      consistency checks pass.

## Non-goals

- Changing the responsive web UI, its phone-sized layout, or Tailscale access.
- Removing `packages/domain-types`; it remains the web client's typed API
  contract.
- Adding a PWA, native notifications, offline support, or another mobile
  replacement.
- Changing API endpoints or the run state machine.
