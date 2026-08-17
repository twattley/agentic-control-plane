# Ticket 024: The round cap must reset when the human speaks

## Summary

`prior_changes` counts every changes-verdict in the run's whole history, and
the cap (`max_review_rounds = 3`) never resets. So the first escalation is
also the last autonomous disagreement the pair will ever have: from then on,
*every* changes-verdict escalates immediately — including on brand-new work
the human just asked for.

Run 4 showed it live. After the initial three-round bounce, the human
requested a loading indicator (new work), answered a JS-fallback question,
and asked for an evidence-line fix — and every single review of those came
back `[escalated to human after N change rounds]` at N = 4, 5, 6. The pair
never got a second round on any of them.

## Status

- State: ready
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - shaped from run 4's tail, where each human note bought
  exactly one builder round before the next verdict escalated regardless of
  content.
- Next: builder claims

## Why

`46b8544` ("give the pair three rounds before escalating") reasoned that the
third round is where the pair settles a fix's own regression — that reasoning
is per-disagreement, not per-run-lifetime. The cap exists to stop an infinite
loop inside *one* argument. Counting a lifetime instead means a long run
degrades into human-gated round-trips: every review needs a human click, which
is precisely the doom-loop feeling the run produced tonight.

## Capability

The escalation cap counts changes-verdicts **since the run's last human word**
— a note posted or a decision taken. Each human intervention grants the pair a
fresh set of rounds on the new instruction. A run with no human involvement
behaves exactly as today.

## Public Interface

- The `prior_changes` computation in `run_pass`
  (`apps/api/app/worker.py`) counts from the most recent
  `human_note_posted` / human decision event rather than from the beginning.
- `_review_outcome` and the recorded escalation facts are unchanged — this
  ticket changes only what gets counted, per `017`'s rule that the verdict
  recorded is the verdict given.

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

- [ ] After a human note, the pair gets the full cap again before the next
      escalation, pinned by a test replaying run 4's shape (3 rounds →
      escalate → human note → changes-verdict does **not** escalate).
- [ ] A run that hits the cap with no human word since its last cap still
      escalates exactly as today.
