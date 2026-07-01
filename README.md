# agentic-control-plane

> Portable agentic control plane for the builder/reviewer agent handoff loop — owns workflow state, locks, append-only events, artifacts, and approvals. Not an executor.

Read `CLAUDE.md` for agent orientation. Read `ARCHITECTURE.md` for design decisions.

## Setup

```bash
cp apps/api/.env.example apps/api/.env
# Edit apps/api/.env and set AGENTIC_CONTROL_PLANE_DATABASE_URL

make install
make init-db
```

## Running

```bash
make serve    # API on :8400
make web      # Web on :5400
make mobile   # Expo
```

## Testing

```bash
make test
```
