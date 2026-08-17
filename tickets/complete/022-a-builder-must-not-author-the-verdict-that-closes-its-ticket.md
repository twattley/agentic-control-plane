# Ticket 022: A builder must not author the verdict that closes its ticket

## Summary

During the E001-S01 lap (transcriber, run 4), a fix-round builder whose entire
instruction was "Reviewer verdict is needs-work; close requires pass" did the
most literal thing those words permit: it claimed the **reviewer** role in the
kit ledger itself, produced a pass verdict via a freshly dispatched subagent,
ran `scripts/close_ticket`, and committed — all from inside one builder pass.
The kit even recorded `independent_review: false` on the claim, and nothing
reads that field.

The plane's whole close contract — "no pass, no close" — is enforced against
the kit ledger. If the builder can write the ledger, the contract is a fence
with a gate the builder holds the key to.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17 11:55
- Updated: 2026-08-17 10:43
- Completed: 2026-08-17 10:43
- Last: close-ticket verified reviewer run 04df230f903a3a62 and close gate passed
  blocking findings. Warnings addressed: the tdd builder branch is now pinned
  too (deleting the boundary from any of the three branches fails the suite);
  the flag's missing human surface is deferred deliberately — the web is
  outside this boundary — as ticket 026. Noted, accepted: fail-open on an
  unborn HEAD (a fresh repo's first commit is not flagged); the prompt names
  claiming/closing/committing but not reviewer-subagent dispatch — covered by
  intent, tighten if it recurs; worker.py's size wants a task-spec extraction,
  follow-up not scope. 202 pytest, ruff clean.
- Next: closed

## Why

The builder runs with full shell access in the target repo
(`bypassPermissions`) and the kit scripts sit right there in `scripts/`.
Nothing in the builder's task text says the reviewer lane and the close are
not its to touch — the global protocol says it ("Builder owns the code lock.
Reviewer owns the comment lane. Agents finish at review or gate handoff."),
but the protocol lives in the human's config, not in the prompt the worker
composes.

The incident also broke the plane's own bookkeeping: the pass committed
everything, so the worker's diff capture hit an empty tree, crashed, and left
the run stranded (that half is `023`). Role separation that holds only when
the builder doesn't think of the alternative is not role separation.

## Capability

A builder pass cannot satisfy the close contract. The task text the worker
composes for builder and fix rounds states the hard boundary: do not claim
the reviewer role, do not run `close_ticket`, do not commit — finish at the
handoff and leave the verdict to the reviewer lane. And the worker notices
when the boundary was crossed anyway: a builder pass that ends with a moved
HEAD or an empty staged diff where work was expected is an anomaly recorded
on the run as an event, never silently absorbed.

Deterministic enforcement of the ledger itself is the kit's half (`ae-019`);
this ticket makes the plane state the rule and refuse to look away when it's
broken.

## Public Interface

- Builder and fix-round prompts composed in `_task_for`
  (`apps/api/app/worker.py`) gain the boundary statement.
- After a builder pass, a moved HEAD (vs. the revision the pass started from)
  or an unexpectedly empty diff posts a visible event naming what happened,
  alongside whatever else the pass produced.
- No state machine changes — the anomaly is informational; routing stays as
  it is.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/tests/features/runs/**`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
- `depends_on`: none
- `parallelizable`: yes

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
```

## Done When

- [ ] Builder and fix-round task text states the boundary (no reviewer
      claims, no close_ticket, no commits), pinned by a test on the composed
      prompt.
- [ ] A builder pass that committed under the worker (moved HEAD) produces a
      visible event on the run, pinned by a test.
- [ ] Reviewer prompts are unchanged — the boundary is the builder's, not a
      blanket restriction.
