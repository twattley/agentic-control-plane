# agentic-control-plane

> Portable agentic control plane for the builder/reviewer agent handoff loop — owns workflow state, locks, append-only events, artifacts, and approvals. Not an executor.

Read `CLAUDE.md` for agent orientation. Read `ARCHITECTURE.md` for design decisions.

## How it works — ticket to completion, from the UI

The goal: you lay out the work, agents carry it end to end, and you only touch
the decisions that are actually yours. Open `http://localhost:5400` (or
`http://server:5400` over Tailscale from your phone) and:

1. **Pick a project.** The homepage lists every git repo in `~/Projects`
   automatically (a `.planeignore` file at a repo's root hides it). The
   **Workbench** at the top shows one pane per in-flight run — the two-sentence
   re-entry summary, who holds it, and what just happened. Runs waiting on
   *you* glow amber.

2. **Shape the work.** Inside a project, either:
   - **Shape an idea** — chat with an agent that runs *in that repo's
     checkout*, so it argues from the real code. When the idea converges, hit
     **Freeze**: the agent writes the final markdown and the plane files it.
   - **+ New story / + New ticket** — write it yourself in the composer.

   On a contract repo (`epic-story-v1` marker in `tickets/README.md`), freezing
   or composing creates a **story under an epic** — identity (`E001-S02`) is
   allocated by the repo's own `scripts/agent_workflow create-story`, and the
   file lands in `tickets/backlog/`. On a legacy repo it's a flat
   `tickets/<slug>.md`.

3. **Mark it ready.** Backlog stories show a **Mark ready** button — the
   shaped-and-scoped gate. Only `ready` stories are startable; the plane
   refuses anything else.

4. **Start work.** Pick who builds and who reviews (e.g. Claude Sonnet builds,
   Codex reviews) and a mode (direct or tests-first). From here the machine
   drives itself:

   ```text
   queued → builder claims → building → brief+diff → awaiting_review
         → reviewer claims → reviewing → VERDICT: pass → awaiting_human
                                       ↘ VERDICT: changes → needs_work → (builder fixes, loop)
   ```

   Each hop spawns a detached worker that runs the agent CLI in the repo
   checkout, posts its results as events, and the state machine dispatches the
   next role. Review bounces are capped (default 3) before escalating to you.

5. **Approve from the Inbox.** The run parks at `awaiting_human` with the
   diff, the brief, and the reviewer's verdict. Approve → close → in a repo
   carrying `scripts/close_ticket`, the closer delegates the whole close to it
   — gate, ticket stamp, lane move, history sweep — then **commits locally**
   (never pushes — pushing stays a human act). A repo without it gets the
   inline close: run the repo's gate command and, on green, commit.

That's the whole loop: shape → freeze → ready → build → review → approve →
commit, with the workbench answering "where did I get to?" whenever you
context-switch.

## Running side by side with the terminal (Herdr / tmux)

The plane holds no private state about work: **the filesystem is the source of
truth**. Tickets are markdown in each repo's `tickets/` folder, lifecycle is
the containing directory, identity lives in the file, and portable handoffs
sit in `.agent-workflow/`. The UI and any terminal workflow read and write the
same files, so you can freeze a story from the phone, claim it from Herdr, and
watch it on the workbench — nothing needs syncing because nothing is copied.

## The ticket contract

Repos opt into the shared `epic-story-v1` contract (canonical doc:
`agentic-engineering/docs/epic-story-workflow-contract.md`; install the kit
with that repo's `install_repo_workflow`). The plane reads each repo's
`scripts/agent_workflow snapshot` to learn its epics, stories, states, and
diagnostics — and delegates story creation to the same tool, so the plane
never invents identities. Repos without the contract still work with flat
tickets.

## Setup

```bash
cp apps/api/.env.example apps/api/.env
# Edit apps/api/.env and set AGENTIC_CONTROL_PLANE_DATABASE_URL

make install
make init-db
```

## Running

```bash
./scripts/start_services   # API :8400 + web :5400 in detached tmux sessions
./scripts/status_all       # sessions + health + last worker activity
./scripts/stop_services

make serve    # or run the API in the foreground
make web      # or run Vite in the foreground
```

Useful `.env` switches: `AGENTIC_CONTROL_PLANE_DISPATCH_ENABLED=true` for the
self-driving loop, `AGENTIC_CONTROL_PLANE_CLAUDE_PERMISSION_MODE=bypassPermissions`
to let a Claude builder run tests unattended. The close gate is not a service
setting: each repo carries its own gate command, set on its project page (or
`PUT /api/v1/repos/{id}/gate`), and a repo without one closes visibly ungated.

## Testing

```bash
make test
```

Tests provision and run against a `<dbname>_test` database — the suite refuses
to touch the live one.
