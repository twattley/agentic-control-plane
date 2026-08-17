# Ticket 030: Choose a skill when shaping a ticket

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
- Phase: shaped
- Started: —
- Updated: 2026-08-17
- Completed: —
- Last: 2026-08-17 - open questions resolved with the owner: dropdown from
  discovered skill directories, per-discussion, chosen at start. Sequenced
  behind 028, which rewrites the same prompt seam this ticket makes swappable.
  Renumbered from 011 (never started) so the shaping lane reads in order.
- Next: builder claims — after 028 lands (shared write scope on
  `discussion_agent.py` and `discussions/**`)

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

## Decisions (owner, 2026-08-17)

- **Where the list comes from:** discovered, not configured. The plane lists
  skill directories on its own host — the user level (`~/.claude/skills/*/SKILL.md`)
  and the repo checkout's level (`.claude/skills/*/SKILL.md`) — and reads each
  skill's frontmatter `name` and `description` for the dropdown. Drop a new
  skill into either directory and it appears on the next fetch; nothing is
  registered anywhere. On a name collision the repo-level skill wins (most
  specific), matching how the CLI resolves scoped skills.
- **Cross-repo worry, resolved:** agentic-engineering stays the canonical
  *authorship* source — skills are written there and reach the skill
  directories (Claude and Codex alike) only through its install/sync. The
  plane deliberately reads the installed layer, not the kit repo, because the
  dropdown's question is *runtime* truth: what a session on this host can
  actually run. That keeps the UI and a terminal pane in exact agreement (a
  skill authored but never installed appears in neither), and spares the
  plane a config path to the kit repo — the same consume-the-installed-
  artifact relationship it already has with the `scripts/` symlinks. The
  standing discipline, not policed by the plane: skills are authored in
  agentic-engineering and installed via its sync, never hand-dropped into
  the skill directories.
- **Per discussion, chosen at start**, like opening a terminal session with
  `/<skill>`. No mid-discussion change — a session shaped half one way and
  half another is hard to read back.
- **Freeze records the skill name** on the discussion, and notes it on the
  frozen ticket so the ticket can be read back knowing how it was produced.
- **Framing mechanism:** the plane reads the chosen skill's `SKILL.md` body
  and carries it into the session via `--append-system-prompt`, alongside the
  base shaping prompt. Deterministic, and independent of whether `/<name>`
  resolution works in `claude -p` print mode.
- **Picking none** keeps the default shaping conversation (as hardened by
  028); the dropdown's empty choice is first-class, not an error.

## Scope

- `allowed_paths`:
  - `apps/api/app/features/discussions/**`
  - `apps/api/app/services/discussion_agent.py`
  - `apps/api/tests/features/discussions/**`
  - `apps/web/src/features/projects/DiscussionPanel.tsx`
  - `apps/web/src/api/hooks.ts`
  - `packages/domain-types/src/index.ts`
  - `tickets/**/030-choose-a-skill-when-shaping-a-ticket.md`
- `read_context_paths`:
  - `ARCHITECTURE.md`
- `forbidden_paths`:
  - `apps/api/app/services/state_machine.py`
  - `apps/api/schema/**`
- `depends_on`:
  - `028-a-ticket-shaped-in-the-ui-must-meet-the-contract-the-loop-enforces`
    (soft: no logical dependency, but 028 rewrites `_SYSTEM`/`FREEZE_PROMPT`
    and this ticket makes that seam skill-swappable — land 028 first)
- `parallelizable`: no — shares `discussion_agent.py` and `discussions/**`
  with ticket 028

## Validation

```bash
uv run --project apps/api pytest apps/api/tests/
cd apps/web && npx tsc -b --noEmit
```

## Done When

- [ ] The dropdown lists skills discovered from the user and repo skill
      directories by reading `SKILL.md` frontmatter — adding a skill file
      makes it appear on the next fetch, with no registration or restart.
- [ ] A shaping discussion can be started with a named skill, or with none.
- [ ] Starting with a skill produces a session framed as that skill would
      frame it in a terminal.
- [ ] Starting with none behaves exactly as it does today.
- [ ] The discussion records which skill shaped it, readable after freeze.
- [ ] An unavailable or misnamed skill fails visibly at start, rather than
      silently degrading to a plain conversation.
