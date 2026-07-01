# schema/

Numbered SQL migration files applied in sort order by `make init-db`.

| File | Description |
|---|---|
| `001_init.sql` | Initial table definitions |

## Rules

- Every statement must be idempotent (`IF NOT EXISTS`, `DO $$ ... $$`).
- Never edit a deployed migration — add a new numbered file.
- Keep `apps/api/app/database.py:_run_migrations()` as the sole runner.
