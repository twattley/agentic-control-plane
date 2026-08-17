# Fast, observable agent roles for dogfooding

## Identity

- `kind`: `epic`
- `epic_id`: `E002`

## Outcome

Dogfooding uses a deliberate agent for each job: Codex shapes tickets quickly,
Sonnet implements at medium effort, and Opus reviews at high effort. A slow
shaping turn is no longer an opaque blocking request: the owner can see that it
is alive, leave and return without duplicating it, or cancel it without losing
the draft or corrupting the discussion.

## Done When

- [ ] Ticket shaping always invokes Codex `gpt-5.6-sol` with high reasoning,
      priority service, and a read-only checkout; it never silently falls back
      to Claude.
- [ ] New work defaults to Claude Sonnet at medium effort for building and
      Claude Opus at high effort for review, while the existing per-run pickers
      still allow exceptions.
- [ ] Every live shaping turn exposes truthful lifecycle progress and a Cancel
      action, survives API reload and panel navigation, and cannot be submitted
      twice.
- [ ] Failed or cancelled turns preserve completed history and retry input,
      and a failed first turn leaves no empty discussion behind.

## Boundaries

- This is a single-owner dogfood flow. Polling persisted lifecycle state is
  sufficient; a general event-streaming platform is not part of the outcome.
- Progress reports lifecycle activity derived from Codex JSONL events. It does
  not expose hidden reasoning or fabricate percentage completion.
- Existing provider pickers remain the exception mechanism. There is no
  shaping-provider picker in this outcome.
- Work-unit hard time limits remain an internal safety backstop, not the
  primary user experience or a promise that a valid long turn will be stopped.

## Stories

- `E002-S00`
- `E002-S01`
- `E002-S02`
