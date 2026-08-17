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

- State: complete
- Phase: done
- Started: 2026-08-17
- Updated: 2026-08-17 06:46
- Completed: 2026-08-17 06:46
- Last: close-ticket verified reviewer run 77df6350073bed2b and close gate passed
  (nothing blocking). Review fixes landed: the delegated gate now runs under
  `bash -lc` so both close paths obey the same shell rules; `gate_failed`
  summaries feed the builder's next fix round (a refusal used to bounce the
  builder with stale findings and no reason); the e2e now asserts the commit
  carried the lane move (clean tree + file list); CompactResult is pinned
  against the real tool's payload; the compact button gates on having the kit,
  not the contract marker. Scope widened, recorded below: README.md +
  HANDOFF.md described the pre-016 close. Review notes folded into follow-ups:
  spawn OSError → acp-018, tail-vs-head truncation → acp-031 (shaped as acp-019, renumbered). Accepted:
  `mark_ready` keeps its own stamp/move — the kit has no promote command, so
  there is nothing to delegate to (Done When reworded to say "close
  lifecycle"); worker.py at ~530 lines wants a prompt-composition split,
  follow-up not scope. 179 pytest, ruff, tsc, build green.
- Next: closed
  against football-api-project (eight completed tickets awaiting a sweep).

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
  - `README.md` (widened 2026-08-17: described the pre-016 close and the
    pre-017 review cap)
  - `HANDOFF.md` (widened 2026-08-17: its known-trap entry is what this
    ticket fixes)
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

- [x] Closing an approved run leaves the ticket stamped complete and in the
      complete lane, with no terminal step. (Pinned end-to-end against the real
      kit: `test_plane_close_runs_the_repos_real_closer_end_to_end` — run
      closed, ticket stamped in `complete/`, lane move inside the commit.)
- [x] Aged history is swept as part of that close, using the repo's own
      compaction window. (The plane passes no `--no-compact`; close_ticket's
      default sweep runs.)
- [x] A closer refusal — red gate, non-pass verdict, wrong lane — surfaces its
      reason in the plane and leaves the run unclosed. (`gate_failed` with the
      refusal verbatim; the reason also becomes the builder's next fix
      instruction rather than a silent bounce.)
- [x] The plane contains no second implementation of the close lifecycle —
      stamping and lane movement at close belong to `close_ticket` alone.
      (`mark_ready`'s backlog→ready promotion stays: the kit has no promote
      command, so there is nothing to delegate to; its output is driven
      through the real kit by the conformance suite.)
- [x] A repo can be compacted on demand from the project view, previewing what
      would move before it moves. (POST /workflow/compact, dry-run by default;
      CompactCard's preview → confirm.)
- [x] A legacy-flat repo with no `close_ticket` still closes as it does today.
      (The inline path is untouched and pinned by test_dispatch.)
