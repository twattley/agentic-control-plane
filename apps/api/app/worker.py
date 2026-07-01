"""One-shot agent worker. Spawned detached by `executor.dispatch`.

  python -m app.worker <run_id> <role> <provider>

A pass is: claim the role lease → run the agent in the repo checkout → (builder)
capture the git diff and post a brief, or (reviewer) post findings. Posting the
event advances the state machine, which dispatches the next agent — so the chain
continues without any polling.

`provider="stub"` runs a fake agent (a tiny repo edit) so the whole chain is
provable without spending real Codex/Claude credits or editing a real repo.
Swap `builder_provider` / `reviewer_provider` to `codex` / `claude` on a real
checkout to go live.
"""

import asyncio
import os
import subprocess
import sys
import urllib.request

import asyncpg

from app.config import settings
from app.features.repos import repository as repos_repo
from app.features.runs.models import ArtifactIn, ClaimIn, EventIn
from app.services import executor, runs_service
from app.services.runs_service import LeaseConflictError
from app.services.state_machine import IllegalTransitionError

_TIMEOUT_S = 1800  # a real build can take a while; a stub returns instantly


def _agent_command(role: str, provider: str, task: str, repo_path: str) -> list[str]:
    if provider == "stub":
        if role == "builder":
            # deterministic tiny edit so the builder produces a real git diff
            return ["bash", "-c", "printf '\\n# built by stub agent\\n' >> AGENT_LOG.md"]
        return ["bash", "-c", "true"]  # reviewer stub: no-op
    if provider == "codex":
        return ["codex", "exec", task, "--sandbox", "workspace-write",
                "--ask-for-approval", "never", "--json", "--cd", repo_path]
    if provider == "claude":
        base = ["claude", "-p", task, "--output-format", "json"]
        return base if role == "reviewer" else base + ["--permission-mode", "acceptEdits"]
    raise ValueError(f"unknown provider: {provider}")


def _git_diff(repo_path: str) -> str:
    """Stage everything the agent touched and return the unified diff."""
    subprocess.run(["git", "-C", repo_path, "add", "-A"], check=False)
    out = subprocess.run(
        ["git", "-C", repo_path, "diff", "--cached"],
        cwd=repo_path, capture_output=True, text=True, check=False,
    )
    return out.stdout


async def run_pass(pool: asyncpg.Pool, run_id: int, role: str, provider: str) -> str:
    """Run one agent pass. Returns 'skipped' | 'done'. Safe to call twice —
    the loser of the claim race returns 'skipped'."""
    try:
        await runs_service.claim(pool, run_id, ClaimIn(role=role, holder=provider))
    except (IllegalTransitionError, LeaseConflictError, runs_service.RunNotFoundError):
        return "skipped"

    detail = await runs_service.run_detail(pool, run_id)
    repo = await repos_repo.get_repo(pool, detail.run.repo_id)
    if repo is None:
        return "skipped"

    task = _task_for(detail, role)
    result = subprocess.run(
        _agent_command(role, provider, task, repo.path),
        cwd=repo.path, capture_output=True, text=True, timeout=_TIMEOUT_S, check=False,
    )
    summary = (result.stdout or "").strip()[:500] or f"{provider} {role} pass complete"

    if role == "builder":
        diff = _git_diff(repo.path)
        if diff.strip():
            await runs_service.attach_artifact(pool, run_id, ArtifactIn(kind="diff", content=diff))
        await runs_service.record_event(
            pool, run_id,
            EventIn(type="builder_brief_posted", actor="builder",
                    payload={"summary": summary, "provider": provider}),
        )
    else:
        verdict = "pass"  # stub always passes; a real reviewer parses its output
        await runs_service.record_event(
            pool, run_id,
            EventIn(type="reviewer_findings_posted", actor="reviewer",
                    payload={"verdict": verdict, "summary": summary, "provider": provider}),
        )
    return "done"


def _task_for(detail, role: str) -> str:
    run = detail.run
    if role == "reviewer":
        return f"Review the changes for {run.ticket_id}: {run.title}. Verdict pass or changes."
    findings = next((e for e in reversed(detail.events)
                     if e.type == "reviewer_findings_posted"), None)
    if findings:
        return (f"Address the reviewer findings on {run.ticket_id}: {run.title}. "
                f"Findings: {findings.payload.get('summary', '')}")
    return f"Implement {run.ticket_id}: {run.title}."


def _log(msg: str) -> None:
    print(f"[worker pid={os.getpid()}] {msg}", flush=True)


def _kick_api(run_id: int) -> None:
    """Ask the long-lived API to dispatch whatever the current state now needs.

    The API is the only process that spawns workers, so the next agent is never
    orphaned. A 409 (nothing to dispatch — e.g. awaiting_human) is expected and
    fine; the chain simply pauses for the human.
    """
    if not settings.dispatch_enabled:
        return
    req = urllib.request.Request(
        f"{settings.api_url}/api/v1/runs/{run_id}/dispatch",
        method="POST",
        headers={"Authorization": f"Bearer {settings.auth_token}"},
    )
    try:
        urllib.request.urlopen(req, timeout=5).read()
        _log(f"kicked API to dispatch next for run={run_id}")
    except Exception as exc:  # noqa: BLE001 — 409/terminal states are expected
        _log(f"kick for run={run_id}: {exc!r}")


async def _main(run_id: int, role: str, provider: str) -> None:
    # Use 127.0.0.1, not "localhost": a worker detached from the async parent can
    # hang on macOS name resolution (mDNSResponder / IPv6 ::1) — a numeric host
    # skips the resolver entirely. Only rewrites a bare localhost host.
    dsn = settings.database_url.replace("@localhost", "@127.0.0.1").replace(
        "//localhost", "//127.0.0.1"
    )
    _log(f"start run={run_id} role={role} provider={provider} db={dsn}")
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=2, timeout=10, command_timeout=60)
    try:
        result = await run_pass(pool, run_id, role, provider)
        _log(f"done run={run_id} role={role} -> {result}")
    except Exception as exc:  # noqa: BLE001 — a detached worker must log, not vanish
        _log(f"FAILED run={run_id} role={role}: {exc!r}")
        raise
    finally:
        await pool.close()


def main() -> None:
    run_id, role, provider = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    executor.suppress_inline()  # this worker never spawns the next; it kicks the API
    asyncio.run(_main(run_id, role, provider))
    _kick_api(run_id)  # API (long-lived) dispatches the next agent


if __name__ == "__main__":
    main()
