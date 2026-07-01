# Coding Standards

## TDD — test first, always

Write one failing test before writing implementation. Vertical slices only:
one test → one implementation → repeat. Never write all tests first.

Tests verify behavior through public interfaces. A test that breaks during
an internal refactor (with no behavior change) is a bad test.

See `instructions/testing-instructions.md` for pytest setup and fixture patterns.

## Data contracts

| Context | Use |
|---|---|
| API request/response bodies | Pydantic models in `features/*/models.py` |
| Internal DTOs between layers | Python **dataclasses** |
| Vectorised / bulk data ops | **pandas** DataFrames |
| TypeScript API contracts | Interfaces in `packages/domain-types/` |

Never use Pydantic for internal data that never crosses an API boundary.
Never use pandas for single-row data.

## Feature structure (backend)

```
app/features/<name>/
  controller.py   FastAPI router — routes only, no SQL
  repository.py   asyncpg queries — no business logic
  models.py       Pydantic models + dataclasses
```

Service logic that doesn't belong in a single repository goes in `app/services/`.

## SQL

- Raw asyncpg only. No ORM.
- All queries in `repository.py`.
- Schema migrations are numbered `.sql` files in `apps/api/schema/`.

## Clean interface design

- Functions do one thing; name them by what they return, not how.
- Deep modules: small surface area, rich implementation.
- Prefer `return early` (guard clauses) over nested conditions.
- No speculative features. Implement what the current test requires.

## Storage defaults

- **PostgreSQL** — primary store for all structured data.
- **S3** — secondary store for blobs, large files, and exports. Add only when
  PostgreSQL's TOAST/bytea is genuinely insufficient.
