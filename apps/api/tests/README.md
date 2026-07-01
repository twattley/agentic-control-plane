# tests/

Backend tests for `agentic-control-plane`. Written with pytest + httpx.

Run with: `make test`

## Structure

Mirror the feature structure:
```
tests/
  conftest.py               shared fixtures
  features/
    <name>/
      test_<behavior>.py
```

## Test database

Set `AGENTIC_CONTROL_PLANE_DATABASE_URL` in `apps/api/.env` to a `_test` database.
Tests hit a real PostgreSQL instance — no mocks.
