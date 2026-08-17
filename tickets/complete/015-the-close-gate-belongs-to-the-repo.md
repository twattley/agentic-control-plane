# Ticket 015: The close gate belongs to the repo, not the service

## Summary

`close_gate_command` is one service-wide setting run in whichever checkout a
run belongs to. Every registered repo has a different test command, so any real
value is correct for exactly one repo and wrong for all the others. The default
is `true` — a no-op — which means the honest choice today is between a gate
that blocks every other repo and no gate at all.

The gate is a property of the repository. Store it there.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17
- Updated: 2026-08-17 06:45
- Completed: 2026-08-17 06:45
- Last: close-ticket verified reviewer run 7283fcd6609510fb and close gate passed
  (nothing blocking; both settle-before-close findings fixed: stale doc
  references to the removed env var, and pre-015 gate events misreading as
  ungated). Scope widened, recorded below: `apps/web/src/api/hooks.ts` (the
  mutation hook belongs with every other hook), `README.md` + `HANDOFF.md`
  (both instructed setting the now-removed env var). Review notes accepted as
  deliberate: discovery reads Makefile/package.json on each scan (negligible
  for a personal projects folder); malformed package.json silently yields no
  suggestion ("never invent" is the required outcome). Follow-ups ticketed:
  018 (slow gate strands a run in closing), 019 (500-char truncation eats
  reviewer instructions). Migration applied to dev DB; existing repos carry no
  gate until set once in the UI.
- Next: closed

## Why

Setting the gate to racing-platform's `uv run python scripts/verify_tests
apps/etl` gave that lap a genuine green-tests gate — 708 passing before the
closer would commit. It also guaranteed that a run in football, trading, or
this repo would fail its close on a command that does not exist there. The
setting has been reverted to the no-op for that reason, so right now an agent
can commit without a single test running.

That is the worse of the two failures. A no-op gate is silent: the run closes,
the commit lands, and nothing reports that nothing was checked.

The same setting also leaked into the test suite —
`test_closer_gate_pass_commits_and_closes` read it from the ambient
environment and passed only while the developer's gate happened to be the
default. It now pins its own, but that is a symptom: a gate read from global
config is a gate nothing owns.

## Capability

Each registered repository carries its own close-gate command, set when it is
registered and editable afterwards. A run's closer executes that repository's
command in that repository's checkout. Registering a repo with no gate is
allowed and visible — the plane must never imply a run was verified when
nothing ran.

## Public Interface

- `repos` gains a nullable `close_gate_command` column; `Repo` and the
  TypeScript mirror gain the field.
- Register and edit surfaces accept it. The register flow suggests the repo's
  documented test command where one is discoverable, and never invents one.
- The closer runs the repo's command. A repo with none records explicitly that
  the close was ungated, as an event on the run — absence of a gate is a fact
  about the run, not a silent default.
- `settings.close_gate_command` is removed rather than kept as a fallback: a
  service-wide default is what produced a gate belonging to nobody.
- The run view shows which gate ran and its outcome.

## Scope

- `allowed_paths`:
  - `apps/api/app/config.py`
  - `apps/api/app/features/repos/**`
  - `apps/api/app/worker.py`
  - `apps/api/schema/*.sql`
  - `apps/api/tests/features/repos/**`
  - `apps/api/tests/features/runs/**`
  - `apps/web/src/features/**`
  - `apps/web/src/api/hooks.ts` (widened 2026-08-17: the edit surface's
    mutation hook belongs with every other hook)
  - `README.md` (widened 2026-08-17: documented the removed env var)
  - `HANDOFF.md` (widened 2026-08-17: same — its known-trap entry told the
    reader to set the setting this ticket deletes)
  - `packages/domain-types/src/index.ts`
- `read_context_paths`:
  - `ARCHITECTURE.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`:
  - none
- `parallelizable`: no

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [x] A repo carries its own close-gate command, set at registration and
      editable later. (`repos.close_gate_command`, suggestion from Makefile
      `test:` target / npm `test` script at registration — never invented;
      `PUT /repos/{id}/gate` + CloseGateCard to edit or clear.)
- [x] The closer runs the command belonging to the run's repo, in that repo.
- [x] A repo with no gate closes, and the run records that it was ungated —
      discoverable in the run view, not inferred from silence. (`gate_passed`
      payload carries `gate_command: null` + an "ungated" summary — the state
      machine is forbidden here, so the fact rides the payload; run view shows
      an amber "closed ungated — nothing was verified" panel and timeline
      label.)
- [x] `settings.close_gate_command` is gone, so no run can inherit a command
      from another repo.
- [x] Two repos with different gate commands both close correctly in the same
      service without either being reconfigured. (Pinned by
      `test_two_repos_close_on_their_own_gates_in_one_service`.)
