"""Dispatch = spawn a one-shot agent worker as a DETACHED subprocess and return.

This is the event-driven engine: a state transition calls `dispatch`, which
fires the next agent and returns immediately — the HTTP request never blocks on
a multi-minute agent pass. `start_new_session=True` detaches the child from the
API process group, so a uvicorn `--reload` (or any API restart) does NOT kill an
in-flight build.

Double-dispatch is self-correcting, not guarded here: the worker's first act is
to claim the role lease, and a duplicate loses the claim race and exits. That is
also what makes the manual "re-run stage" button safe.
"""

import os
import subprocess
import sys
from pathlib import Path

from app.config import ROLE_FOR_STATE, settings

_API_DIR = Path(__file__).resolve().parent.parent.parent  # apps/api
_WORKER_LOG = _API_DIR / "logs" / "worker.log"

# Only the long-lived API server spawns workers. A worker that spawned the next
# worker and then exited would orphan it mid-connect (a detached child can't
# finish its DB I/O once its parent dies). So workers call `suppress_inline` and
# instead HTTP-"kick" the API when done; the API dispatches from its always-alive
# process. This keeps every spawned worker parented to a stable process.
_inline = True


def suppress_inline() -> None:
    """Called by a worker: don't spawn here, the worker will kick the API."""
    global _inline
    _inline = False


def dispatch(run_id: int, role: str, provider: str | None = None) -> None:
    """Fire the agent that owns `role` for this run. Fire-and-forget.

    The child gets an explicit env (not just inheritance) and its own log file,
    so a detached worker never depends on the API's fds or ambient environment.
    """
    provider = provider or _provider_for(role)
    env = {
        **os.environ,
        "AGENTIC_CONTROL_PLANE_DATABASE_URL": settings.database_url,
        "AGENTIC_CONTROL_PLANE_DISPATCH_ENABLED": str(settings.dispatch_enabled),
        "AGENTIC_CONTROL_PLANE_BUILDER_PROVIDER": settings.builder_provider,
        "AGENTIC_CONTROL_PLANE_REVIEWER_PROVIDER": settings.reviewer_provider,
        "AGENTIC_CONTROL_PLANE_API_URL": settings.api_url,
        "AGENTIC_CONTROL_PLANE_AUTH_TOKEN": settings.auth_token,
    }
    _WORKER_LOG.parent.mkdir(exist_ok=True)
    log = open(_WORKER_LOG, "a")  # noqa: SIM115 — handed to the child, closed on exit
    subprocess.Popen(
        [sys.executable, "-m", "app.worker", str(run_id), role, provider],
        cwd=str(_API_DIR),
        start_new_session=True,
        env=env,
        stdout=log,
        stderr=log,
    )


def maybe_dispatch(run_id: int, state: str) -> None:
    """Auto-dispatch the owner of `state`, if enabled. No-op inside a worker
    (inline suppressed) — the worker kicks the API to dispatch instead."""
    if not settings.dispatch_enabled:
        return
    role = ROLE_FOR_STATE.get(state)
    if role and _inline:
        dispatch(run_id, role)


def _provider_for(role: str) -> str:
    return settings.reviewer_provider if role == "reviewer" else settings.builder_provider
