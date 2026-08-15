# Ticket 011: Choose a skill when shaping a ticket

## Summary

The shaping panel starts a plain conversation. In the terminal you would open
the same conversation with `/grill-to-tests` or another skill and get a
sharper session — a specific interrogation rather than a general chat. The UI
has no way to say which skill to shape with, so the best shaping technique is
only available to whoever is sitting at a terminal.

Let the operator pick a skill when starting a shaping discussion, so the
browser and the terminal reach the same quality of ticket.

## Status

- State: ready
- Phase: queued
- Started: —
- Updated: 2026-08-15
- Completed: —
- Last: 2026-08-15 - filed from a Control Plane session; the gap surfaced while
  shaping the football stories, where the terminal skills were the better tool
  and the UI could not reach them
- Next: builder

## Why

The point of the UI is that a ticket can go from idea to ready without a
terminal. Shaping is the step where that matters most — it is the one place a
human and an agent genuinely negotiate, and it decides whether everything
downstream is worth running.

Right now the UI's shaping is a general conversation, while the terminal has
purpose-built skills for it. That is backwards: the interface meant to remove
friction offers the weaker tool, so the good technique stays behind the
terminal it was supposed to replace.

## Capability

When starting a shaping discussion, the operator picks a skill from those the
repo and the user have available, or picks none for today's plain
conversation. The chosen skill frames the session the way typing `/<skill>`
would, and the discussion records which skill shaped it — so a frozen ticket
can be read back knowing how it was produced.

## Open Questions

- **Where does the skill list come from?** User-level (`~/.claude/skills`),
  repo-level (`.claude/skills`), or both. Both is the honest answer, but it
  needs a rule for name collisions.
- **Does the skill apply per discussion or per message?** Per discussion is
  simpler and matches how a terminal session behaves.
- **Can the skill change mid-discussion?** Probably not — a session shaped
  half one way and half another is hard to read back.
- **What does freeze do with it?** At minimum record the skill name on the
  discussion. Possibly note it on the frozen ticket.

## Scope

- `allowed_paths`:
  - `apps/api/app/features/discussions/**`
  - `apps/api/app/services/discussion_agent.py`
  - `apps/api/tests/features/discussions/**`
  - `apps/web/src/features/projects/DiscussionPanel.tsx`
  - `apps/web/src/api/hooks.ts`
  - `packages/domain-types/src/index.ts`
  - `tickets/**/011-choose-a-skill-when-shaping-a-ticket.md`
- `read_context_paths`:
  - `ARCHITECTURE.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/schema/**`
- `depends_on`:
  - none
- `parallelizable`: yes

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [ ] A shaping discussion can be started with a named skill, or with none.
- [ ] Starting with a skill produces a session framed as that skill would
      frame it in a terminal.
- [ ] Starting with none behaves exactly as it does today.
- [ ] The discussion records which skill shaped it, readable after freeze.
- [ ] An unavailable or misnamed skill fails visibly at start, rather than
      silently degrading to a plain conversation.
