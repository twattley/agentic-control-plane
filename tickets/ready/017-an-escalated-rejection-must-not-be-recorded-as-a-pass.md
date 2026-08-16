# Ticket 017: An escalated rejection must not be recorded as a pass

## Summary

When a run hits `max_review_rounds`, the reviewer's `changes` verdict is
rewritten to `pass` so the state machine routes to `awaiting_human` instead of
bouncing to the builder again. The routing is right. Overwriting the verdict to
achieve it is not: the run then records that the reviewer passed work the
reviewer rejected.

Separate the two facts. Keep the verdict the reviewer gave, and carry the
escalation as its own flag that the routing reads.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-16
- Completed: —
- Last: 2026-08-16 - found on transcriber run 3, where a third-round `changes`
  was stored as `pass`
- Next: builder claims

## Why

`worker.py:247`:

```python
def _capped_verdict(verdict: str, prior_changes: int, cap: int) -> str:
    """Flip a 'changes' verdict to 'pass' (escalate to human) once the run has
    already bounced back to the builder `cap` times."""
    if verdict == "changes" and prior_changes >= cap:
        return "pass"
```

The truth survives only as a prose prefix on the summary — `[escalated to human
after 2 change rounds]` — while the structured field, which is what everything
downstream reads, says the opposite.

Three consequences, worst last:

1. The run view shows a green pass over a rejection, so a human skimming to
   approve is told the reviewer was satisfied when it was not.
2. `_task_for` selects the newest instruction by event type; a `pass`-labelled
   findings event still carries its real text, but any future logic that
   filters on verdict will silently skip a live rejection.
3. **`close_ticket` gates on the latest reviewer verdict being `pass`.** An
   escalated rejection therefore satisfies a safety gate whose entire purpose
   is to stop exactly that. On transcriber run 3 the final reviewer message
   read `VERDICT: changes` and the stored verdict read `pass`.

The cap itself is right and stays: bouncing a run forever between two models is
worse than asking a human. This is only about telling the truth while doing it.

## Capability

A reviewer's verdict is recorded as the reviewer gave it. A run that has
exhausted its change rounds routes to the human for decision, and that
escalation is visible as a fact of its own — in the event, in the run view, and
to anything gating on review outcome.

## Public Interface

- `reviewer_findings_posted` keeps the reviewer's actual verdict and gains an
  `escalated: bool` in its payload. The prose prefix stops being the only
  record.
- Routing to `awaiting_human` reads the escalation flag rather than a rewritten
  verdict, so `_capped_verdict` disappears rather than being renamed.
- The run view distinguishes "reviewer passed" from "reviewer rejected, rounds
  exhausted, over to you" — these are opposite situations and must not share a
  badge.
- Anything gating on review outcome treats an escalated `changes` as a
  rejection. A human may still override, as today, but explicitly.
- `max_review_rounds` behaviour is otherwise unchanged.

## Scope

- `allowed_paths`:
  - `apps/api/app/worker.py`
  - `apps/api/app/features/runs/models.py`
  - `apps/api/tests/features/runs/**`
  - `apps/web/src/features/runs/**`
  - `packages/domain-types/src/index.ts`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `apps/api/app/config.py`
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

- [ ] A reviewer returning `changes` on the round that exhausts the cap has
      `changes` stored as its verdict, with `escalated` true.
- [ ] That run still routes to `awaiting_human` — the cap keeps working.
- [ ] A genuine `pass` is indistinguishable from today and carries no
      escalation flag.
- [ ] The run view shows an escalated rejection differently from a pass.
- [ ] A test pins that an escalated rejection does not satisfy a check for a
      passing review.
- [ ] `_capped_verdict` no longer exists.
