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
import json
import os
import signal
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
        # exec is non-interactive (no approval prompts); the sandbox governs writes.
        return ["codex", "exec", task, "-s", "workspace-write", "-C", repo_path]
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
    if role == "closer":
        return await _close_pass(pool, run_id)

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
    summary = _agent_message(result.stdout or "", provider).strip()[:500] \
        or f"{provider} {role} pass complete"

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
        verdict = _parse_verdict(result.stdout or "", provider)
        prior_changes = sum(
            1 for e in detail.events
            if e.type == "reviewer_findings_posted" and e.payload.get("verdict") == "changes"
        )
        verdict = _capped_verdict(verdict, prior_changes, settings.max_review_rounds)
        if verdict == "pass" and prior_changes >= settings.max_review_rounds:
            summary = f"[escalated to human after {prior_changes} change rounds] {summary}"
        await runs_service.record_event(
            pool, run_id,
            EventIn(type="reviewer_findings_posted", actor="reviewer",
                    payload={"verdict": verdict, "summary": summary, "provider": provider}),
        )
    return "done"


async def _close_pass(pool: asyncpg.Pool, run_id: int) -> str:
    """Run the close gate, then commit the run's changes in the repo checkout.

    Gate green -> `gate_passed` (state closing -> closed). Gate red -> `gate_failed`
    (back to needs_work for a fix). Commits locally; never pushes (that stays a
    deliberate human/CI action). Safe to run twice: a second closer finds the run
    already past `closing` and the transition raises -> skipped.
    """
    detail = await runs_service.run_detail(pool, run_id)
    if detail.run.state != "closing":
        return "skipped"
    repo = await repos_repo.get_repo(pool, detail.run.repo_id)
    if repo is None:
        return "skipped"

    gate = subprocess.run(
        ["bash", "-lc", settings.close_gate_command],
        cwd=repo.path, capture_output=True, text=True, timeout=_TIMEOUT_S, check=False,
    )
    if gate.returncode != 0:
        return await _post_gate(
            pool, run_id, "gate_failed",
            (gate.stdout + gate.stderr).strip()[:500] or "gate command failed",
        )

    subprocess.run(["git", "-C", repo.path, "add", "-A"], check=False)
    commit = subprocess.run(
        ["git", "-C", repo.path,
         "-c", "user.email=agent@control-plane", "-c", "user.name=agentic-control-plane",
         "commit", "-m", f"{detail.run.ticket_id}: {detail.run.title}"],
        capture_output=True, text=True, check=False,
    )
    note = commit.stdout.strip()[:300] or commit.stderr.strip()[:300] or "committed"
    return await _post_gate(pool, run_id, "gate_passed", note)


async def _post_gate(pool: asyncpg.Pool, run_id: int, event_type: str, summary: str) -> str:
    try:
        await runs_service.record_event(
            pool, run_id, EventIn(type=event_type, actor="system", payload={"summary": summary})
        )
    except IllegalTransitionError:
        return "skipped"  # another closer already moved it
    return "done"


def _agent_message(stdout: str, provider: str) -> str:
    """The human-readable final message. Claude's `-p --output-format json` wraps
    it in a `result` field; other providers print plain text."""
    if provider == "claude":
        try:
            return json.loads(stdout).get("result", stdout)
        except (json.JSONDecodeError, AttributeError):
            return stdout
    return stdout


def _parse_verdict(stdout: str, provider: str) -> str:
    """Extract 'pass' | 'changes' from an agent's review output.

    The reviewer is asked to end with a `VERDICT: pass|changes` line. Ambiguous
    output defaults to 'pass' so we escalate to the human rather than loop the
    builder forever. A stub reviewer emits nothing -> 'pass'.
    """
    low = _agent_message(stdout, provider).lower()
    if "verdict: changes" in low or "verdict:changes" in low:
        return "changes"
    return "pass"


def _capped_verdict(verdict: str, prior_changes: int, cap: int) -> str:
    """Flip a 'changes' verdict to 'pass' (escalate to human) once the run has
    already bounced back to the builder `cap` times."""
    if verdict == "changes" and prior_changes >= cap:
        return "pass"
    return verdict


def _task_for(detail, role: str) -> str:
    run = detail.run
    if role == "reviewer":
        diff = next((a.content for a in reversed(detail.artifacts) if a.kind == "diff"), "")
        return (
            f"Review this diff for {run.ticket_id}: {run.title}.\n"
            "Assess correctness and safety. End your reply with exactly one line: "
            "'VERDICT: pass' if it correctly and safely implements the task, or "
            "'VERDICT: changes' followed by what must be fixed.\n\n"
            f"DIFF:\n{diff}"
        )
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
    # A worker spawned by the async API server (uvicorn/uvloop) inherits a blocked
    # signal mask that survives exec and stalls the child's async DB I/O. Clear it.
    try:
        signal.pthread_sigmask(signal.SIG_SETMASK, set())
    except (AttributeError, OSError):
        pass
    run_id, role, provider = int(sys.argv[1]), sys.argv[2], sys.argv[3]
    executor.suppress_inline()  # this worker never spawns the next; it kicks the API
    asyncio.run(_main(run_id, role, provider))
    _kick_api(run_id)  # API (long-lived) dispatches the next agent


if __name__ == "__main__":
    main()
