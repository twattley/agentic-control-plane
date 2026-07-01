# apps/api — Python FastAPI

## Stack

- **FastAPI** — web framework
- **asyncpg** — raw SQL (no ORM)
- **pydantic-settings** — config from env

## Source layout

```
app/
  features/      one folder per domain feature
    <name>/
      controller.py   FastAPI router
      repository.py   asyncpg queries
      models.py       Pydantic models + dataclasses
  services/      shared logic (LLM clients, algorithms, etc.)
  cli.py         `agentic-control-plane serve` and `agentic-control-plane init-db`
  config.py      pydantic-settings Config
  database.py    asyncpg pool + migration runner
  main.py        FastAPI app + CORS + lifespan
schema/
  001_init.sql   initial table definitions
tests/
  conftest.py    db pool + httpx client fixtures
```

## Commands

```bash
make serve      # FastAPI on :8400 with --reload
make init-db    # apply schema/*.sql
make test       # pytest
```

## Environment variables

| Variable | Description |
|---|---|
| `AGENTIC_CONTROL_PLANE_DATABASE_URL` | PostgreSQL connection string (required) |
