# Ticket 016: Closing in the plane runs the repo's own closer

## Summary

Closing a run in the plane runs the gate and commits. It does not stamp the
ticket complete, does not move it out of `in-progress/`, and does not sweep
aged history into the done ledger. The repo's own `scripts/close_ticket` does
all three, and the plane never calls it.

So a ticket closed from the UI stays in the in-progress lane forever and the
completed lane grows without bound — the exact mess compaction was built to
prevent, reachable only from a terminal.

Stop reimplementing half of close. Delegate to the closer the repo already
carries, and expose compaction as an action in its own right for the backlogs
that have already accumulated.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-16
- Completed: —
- Last: 2026-08-16 - noticed while squaring up after the S001 lap, where the
  ticket had to be closed from a terminal after the plane said it was done
- Next: builder claims, after 014

## Why

The two closers split the job and neither knows it:

| | plane | `close_ticket` |
| --- | --- | --- |
| gate | yes | yes |
| commit | yes | no, by design |
| stamp + move lane | **no** | yes |
| sweep aged history | **no** | yes |

After the S001 run reached `closed`, the ticket was still sitting in
`tickets/in-progress/` and the run's own board still counted it as live. Closing
it properly meant a terminal, and four manual repairs before the portable closer
would accept the file.

The backlog is not hypothetical: football-api-project currently has eight
completed tickets a sweep would clear, and it has no route to that except a
command line.

`close_ticket` already refuses to close on a bad gate, a non-pass reviewer
verdict, or a ticket outside the in-progress lane. Those refusals are the
contract, and routing the plane through it means the UI inherits them instead
of quietly having weaker rules than the terminal.

## Capability

Closing an approved run runs the repository's own closer: gate, stamp, lane
move, and the aged-history sweep. Its refusals surface in the plane as the
reason the close did not happen, with the run left where it was rather than
marked closed.

Separately, a repository can be compacted on demand, with a preview of what
would be swept before anything moves.

## Public Interface

- The closer invokes `scripts/close_ticket` in the run's checkout for the run's
  work unit, with the repo's gate command, and commits after it succeeds.
- A non-zero exit is surfaced verbatim as the close failure reason and recorded
  as an event. The run does not reach `closed`.
- The plane stops stamping or moving ticket files itself — one implementation
  of the ticket lifecycle, in the portable kit.
- `POST /repos/{id}/workflow/compact` runs `agent_workflow compact`, accepting
  the flags the CLI already takes (`--before`, `--dry-run`).
- The project view gains a compact action showing the dry-run result — which
  tickets and runs would move — and requiring confirmation before the sweep.
- Repos with no `close_ticket` (legacy-flat, no contract) keep today's
  behaviour rather than failing.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/features/workflow/**`
  - `apps/api/tests/features/workflow/**`
  - `apps/api/tests/features/runs/**`
  - `apps/web/src/features/projects/**`
  - `apps/web/src/api/hooks.ts`
  - `packages/domain-types/src/index.ts`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `tickets/ready/014-a-plane-authored-ticket-must-close-with-the-portable-closer.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`:
  - `014-a-plane-authored-ticket-must-close-with-the-portable-closer`
- `parallelizable`: no

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [ ] Closing an approved run leaves the ticket stamped complete and in the
      complete lane, with no terminal step.
- [ ] Aged history is swept as part of that close, using the repo's own
      compaction window.
- [ ] A closer refusal — red gate, non-pass verdict, wrong lane — surfaces its
      reason in the plane and leaves the run unclosed.
- [ ] The plane contains no second implementation of stamping or lane movement.
- [ ] A repo can be compacted on demand from the project view, previewing what
      would move before it moves.
- [ ] A legacy-flat repo with no `close_ticket` still closes as it does today.
