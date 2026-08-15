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
from pathlib import Path

import asyncpg

from app.config import settings
from app.features.repos import repository as repos_repo
from app.features.runs.models import ArtifactIn, ClaimIn, EventIn
from app.features.workflow import repository as workflow_repo
from app.services import executor, runs_service
from app.services.runs_service import LeaseConflictError
from app.services.state_machine import IllegalTransitionError

_TIMEOUT_S = 1800  # a real build can take a while; a stub returns instantly


def _split_spec(provider: str) -> tuple[str, str]:
    """A provider spec is "provider[:model]" — e.g. "claude:sonnet", "codex"."""
    base, _, model = provider.partition(":")
    return base, model


def _agent_command(role: str, provider: str, task: str, repo_path: str) -> list[str]:
    base, model = _split_spec(provider)
    if base == "stub":
        if role == "builder":
            # deterministic tiny edit so the builder produces a real git diff
            return ["bash", "-c", "printf '\\n# built by stub agent\\n' >> AGENT_LOG.md"]
        return ["bash", "-c", "true"]  # reviewer stub: no-op
    if base == "codex":
        # exec is non-interactive (no approval prompts); the sandbox governs writes.
        cmd = ["codex", "exec", task, "-s", "workspace-write", "-C", repo_path]
        return cmd + ["-m", model] if model else cmd
    if base == "claude":
        cmd = ["claude", "-p", task, "--output-format", "json"]
        if model:
            cmd += ["--model", model]
        if role != "reviewer":  # reviewer is read-only; builder needs write perms
            cmd += ["--permission-mode", settings.claude_permission_mode]
        return cmd
    raise ValueError(f"unknown provider: {provider}")


ARTIFACT_DIR = ".agent-artifacts"


def _capture_evidence(repo_path: str, run_id: int) -> str | None:
    """Take the builder's optional markdown evidence out of the checkout.

    Removing the file is part of capturing it: evidence belongs to the run, not
    to the repository. Removal is the tidy path, not the guarantee — a pass that
    crashes between write and capture leaves the file behind, so `_stage_all`
    holds the invariant that evidence never reaches a diff or a commit.
    """
    path = Path(repo_path) / ARTIFACT_DIR / f"{run_id}.md"
    if not path.is_file():
        return None
    content = path.read_text()
    path.unlink()
    return content


def _stage_all(repo_path: str) -> None:
    """Stage everything the agent touched, except the artifact directory.

    Every `git add -A` in the pipeline goes through here. The exclusion is what
    keeps evidence — this run's or a crashed earlier run's — out of the diff the
    reviewer reads and out of the commit the closer writes. Resetting the path
    first also removes evidence that the agent staged before returning; a
    negative pathspec alone does not change entries already in the index.
    """
    subprocess.run(
        ["git", "-C", repo_path, "reset", "--quiet", "--", ARTIFACT_DIR],
        check=False,
    )
    subprocess.run(
        ["git", "-C", repo_path, "add", "-A", "--", ".", f":(exclude){ARTIFACT_DIR}"],
        check=False,
    )


def _git_diff(repo_path: str) -> str:
    """Stage everything the agent touched and return the unified diff."""
    _stage_all(repo_path)
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
        detail = await runs_service.run_detail(pool, run_id)
    except runs_service.RunNotFoundError:
        return "skipped"
    repo = await repos_repo.get_repo(pool, detail.run.repo_id)
    if repo is None:
        return "skipped"

    # Resolve the specification before taking the lease. Unsafe or ambiguous
    # snapshot locators must fail visibly while leaving the run inert.
    task = _task_for(detail, role, repo.path)

    try:
        await runs_service.claim(pool, run_id, ClaimIn(role=role, holder=provider))
    except (IllegalTransitionError, LeaseConflictError, runs_service.RunNotFoundError):
        return "skipped"

    result = subprocess.run(
        _agent_command(role, provider, task, repo.path),
        cwd=repo.path, capture_output=True, text=True, timeout=_TIMEOUT_S, check=False,
    )
    summary = _agent_message(result.stdout or "", provider).strip()[:500] \
        or f"{provider} {role} pass complete"

    if role == "builder":
        # Capture first for a tidy checkout. `_stage_all` separately protects
        # the index from stale or already-staged artifact files.
        evidence = _capture_evidence(repo.path, run_id)
        diff = _git_diff(repo.path)
        if diff.strip():
            await runs_service.attach_artifact(pool, run_id, ArtifactIn(kind="diff", content=diff))
        if evidence:
            await runs_service.attach_artifact(
                pool, run_id, ArtifactIn(kind="evidence", content=evidence)
            )
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

    _stage_all(repo.path)
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
    if _split_spec(provider)[0] == "claude":
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


def _task_for(detail, role: str, repo_path: str) -> str:
    run = detail.run
    spec = _spec_note(repo_path, run.ticket_id)
    if role == "reviewer":
        diff = next((a.content for a in reversed(detail.artifacts) if a.kind == "diff"), "")
        return (
            f"Review this diff for {run.ticket_id}: {run.title}.{spec}\n"
            "Assess correctness and safety. End your reply with exactly one line: "
            "'VERDICT: pass' if it correctly and safely implements the task, or "
            "'VERDICT: changes' followed by what must be fixed.\n\n"
            f"DIFF:\n{diff}{_evidence_review_note(detail)}"
        )
    findings = next((e for e in reversed(detail.events)
                     if e.type == "reviewer_findings_posted"), None)
    evidence = _evidence_invitation(run.id)
    if findings:
        return (f"Address the reviewer findings on {run.ticket_id}: {run.title}.{spec} "
                f"Findings: {findings.payload.get('summary', '')}{evidence}")
    if run.mode == "tdd":
        return (f"Implement {run.ticket_id}: {run.title}.{spec} Work test-first: write a "
                "failing test that captures the behaviour, then implement until it "
                f"passes.{evidence}")
    return f"Implement {run.ticket_id}: {run.title}.{spec}{evidence}"


def _evidence_invitation(run_id: int) -> str:
    """Invite evidence; never require it. Work with nothing to demonstrate — a
    refactor, a rename — writes nothing, and that is a complete pass."""
    return (
        " Optional: if this change has a demonstrable outcome, write markdown to "
        f".agent-artifacts/{run_id}.md — a table of the ticket's scenarios with real "
        "inputs and the ACTUAL outputs you got from running the code, never claims "
        "about what it would do. Write nothing if there is nothing to demonstrate "
        "— that is still a complete pass."
    )


def _evidence_review_note(detail) -> str:
    """Show the reviewer the builder's evidence, and tell it what would make the
    evidence worthless."""
    evidence = next(
        (a.content for a in reversed(detail.artifacts) if a.kind == "evidence"), ""
    )
    if not evidence:
        return ""
    return (
        "\n\nEVIDENCE the builder attached — a case table it claims to have run. "
        "Check it against the diff: if the cases could not have been run, or the "
        "outputs contradict the code, that is 'VERDICT: changes'.\n"
        f"{evidence}"
    )


def _spec_note(repo_path: str, ticket_id: str) -> str:
    """If the checkout has a ticket file for this run, every prompt points at it —
    the file, not the run title, is the full spec."""
    workflow = workflow_repo.load_workflow(repo_path)
    try:
        document = workflow_repo.document_from_workflow(
            repo_path, workflow, ticket_id
        )
    except workflow_repo.WorkflowDocumentError:
        if workflow.source == "legacy-flat":
            return ""
        raise
    note = f" The full specification is in {document.path} — read it first."
    return note + _epic_note(workflow, ticket_id)


def _epic_note(workflow, ticket_id: str) -> str:
    """The point of the epic hierarchy: frame the story's small goal inside the
    epic's big one, so the agent knows what the slice is FOR — and its boundary."""
    story = next((s for s in workflow.stories if s.story_id == ticket_id), None)
    if story is None:
        return ""
    epic = next((e for e in workflow.epics if e.epic_id == story.epic_id), None)
    if epic is None:
        return ""
    return (
        f" This story is one slice of epic {epic.epic_id}: {epic.title} "
        f"({epic.path}) — read the epic for the broader goal it serves, "
        "then deliver only this story."
    )


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
