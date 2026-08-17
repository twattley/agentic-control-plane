# Agent Workflow

Local file-based handoff state for builder/reviewer agent work.

- Run files live under `runs/`.
- Treat `runs/` as runtime coordination state unless you explicitly want an
  auditable handoff record.
- Add `.agent-workflow/runs/` to `.gitignore` for the default local-only mode.
