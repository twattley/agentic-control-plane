# Ticket 035: Start a shaping discussion from a bug or feature template

## Summary

The shaping panel (`DiscussionPanel`, built by acp-028 and acp-030) opens a
discussion from a single blank "draft" box. But a bug and a feature each carry
the same handful of fields every time, so the human types them from nothing and
the agent then quizzes from zero — a longer back-and-forth than the shape needs.

Offer a template at the start of a discussion — **Bug**, **Feature**, or
**none** (today's blank box). Choosing one shows the matching fields, and
filling them composes a well-formed opening message that seeds the discussion
exactly as a typed draft does now. The structured start gets the ticket roughly
half the way there before the agent engages; the agent still quizzes the gaps.

## Status

- State: complete
- Phase: done
- Started: 2026-08-17
- Updated: 2026-08-17 15:26 BST
- Completed: 2026-08-17 15:26 BST
- Last: closed by hand — this legacy ticket had no ledger run (built by a
  dispatched frontend agent, reviewed by the owner's live spot-check on :5400,
  approved "looks good"). Close gate `npx tsc -b --noEmit` re-run at close:
  pass. Read-only composed preview accepted as built.
- Next: closed

## Why

The point of the UI is that a ticket can go from idea to ready without a
terminal (acp-030's ruling). The opening message is where that starts, and a
blank box is the weakest possible start: it asks the human to remember the shape
of a good bug or feature report every time, and it gives the agent nothing to
work from, so the first few exchanges are spent reconstructing fields the human
already knew.

The owner's layering decision for this work: the **form** is a UI concern and
lives in this repo; the **quizzing** stays portable and unchanged. The template
does not reimplement any agent behavior — it only composes the `draft` string
the existing start-discussion flow already accepts, then hands off to the
shaping skills (selectable since acp-030) to interrogate the rest. We
deliberately do not make the field sets portable markdown the plane renders;
that is over-engineering for a single-owner tool, and promoting field
definitions to the kit is cheap later if terminal parity is ever wanted.

## Capability

When starting a new shaping discussion, the operator picks a template alongside
the existing skill dropdown, epic select, and slug:

- **Bug** — fields: *what I try to do*, *what actually happens*, *what should
  happen*, *where* (app, page, area), and an optional *error / logs*.
- **Feature** — fields: *what I want*, *why* (what it unblocks), *who it's
  for*, *what "done" looks like*, and optional *constraints*.
- **None** — the blank draft box, behaving exactly as it does today. This is
  first-class, not an error, and remains the default.

Filling a template's fields composes a single opening message in a stable,
labelled shape (each field a short bolded heading followed by the value), and
that message becomes the `draft` the start-discussion flow already sends.
Optional fields left empty are omitted from the composed message rather than
emitted as empty headings. From the moment the discussion starts, nothing
downstream can tell the message came from a template rather than a typed draft —
the skill framing, freeze, and contract-valid ticket path (acp-028, acp-030)
are untouched.

## Scope

- `allowed_paths`:
  - `apps/web/src/features/projects/DiscussionPanel.tsx`
  - `apps/web/src/features/projects/discussionTemplates.ts`
  - `tickets/**/035-start-a-shaping-discussion-from-a-template.md`
- `read_context_paths`:
  - `ARCHITECTURE.md`
  - `apps/web/src/api/hooks.ts`
  - `tickets/complete/030-choose-a-skill-when-shaping-a-ticket.md`
  - `tickets/complete/028-a-ticket-shaped-in-the-ui-must-meet-the-contract-the-loop-enforces.md`
- `forbidden_paths`:
  - `apps/api/**`
  - `apps/web/src/api/hooks.ts`
  - `apps/web/src/features/projects/ProjectView.tsx`
  - `packages/domain-types/**`
- `depends_on`:
  - none (acp-028 and acp-030 built the panel and skill dropdown this sits
    beside; both are complete)
- `parallelizable`: yes — confined to `DiscussionPanel.tsx` and a new
  `discussionTemplates.ts` helper. E002-S00 forbids `DiscussionPanel.tsx` and
  owns `ProjectView.tsx` and `__tests__/**`, which this story now forbids or
  avoids; the two touch no common file.

## Validation

```bash
cd apps/web && npx tsc -b --noEmit
```

The compose step lives in a pure, typed `discussionTemplates.ts` helper so its
correctness is legible from the types and a glance. Per the owner's standing
call, the frontend carries no automated tests — the owner dogfoods and verifies
the UI by hand, and a reversible UI slip is fixed on sight, not guarded against.

## Done When

- [x] A new discussion can be started with a Bug template, a Feature template,
      or none; none is the default and behaves exactly as today.
- [x] Choosing Bug or Feature shows that template's fields; filling them
      composes the opening `draft` in a stable, labelled shape.
- [x] Optional fields left blank are omitted from the composed message, not
      emitted as empty headings.
- [x] The composed message is sent through the existing start-discussion path
      with no new API, hook, contract, or schema change.
- [x] `npx tsc -b --noEmit` passes; the owner spot-checked Bug, Feature, and
      none in the running app.

## Non-goals

- No agent-side change: the shaping skills, freeze, and contract enforcement
  (acp-028, acp-030) are untouched — the template only shapes the opening
  message they receive.
- No portable/data-driven template definitions and no plane rendering of kit
  markdown; the field sets live in this UI. Promotion to the kit is a later
  decision if terminal parity is ever wanted.
- No new template kinds beyond Bug and Feature in this slice.
- No persistence of which template was used; unlike the shaping skill
  (acp-030), the template is a transient input to the opening message, not a
  property of the discussion.
