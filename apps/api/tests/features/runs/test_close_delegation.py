"""Closing in the plane runs the repo's own closer (acp-016).

A repo that carries `scripts/close_ticket` owns the whole close: stamp, lane
move, sweep. The plane's closer delegates to it — with the repo's own gate —
and commits only after it succeeds. Its refusals surface as the reason the
close did not happen, with the run left unclosed. A repo without the script
keeps the plane's inline gate-and-commit behaviour (pinned by test_dispatch)."""

import subprocess

from app import worker
from app.worker import run_pass
from tests.conftest import AUTH
from tests.features.runs.test_dispatch import (
    _drive_to_closing,
    _gate_event,
    _git_repo,
    _run_on,
    _state,
)


def _install_closer(
    repo_dir, exit_code: int = 0, stderr: str = "", delay_s: float = 0
) -> None:
    """A fake close_ticket that records its argv and exits as told. The real
    one is pinned by the portable-close conformance suite; this one isolates
    the plane's half of the seam."""
    scripts = repo_dir / "scripts"
    scripts.mkdir(exist_ok=True)
    closer = scripts / "close_ticket"
    closer.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> closer_args.log\n'
        + (f"sleep {delay_s}\n" if delay_s else "")
        + (f'printf "%s\\n" "{stderr}" >&2\n' if stderr else "")
        + f"exit {exit_code}\n"
    )
    closer.chmod(0o755)


def _closer_argv(repo_dir) -> str:
    calls = (repo_dir / "closer_args.log").read_text().splitlines()
    assert len(calls) == 1, calls
    return calls[0]


async def test_close_delegates_to_the_repos_closer_with_its_gate(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_closer(repo_dir)
    run_id = await _run_on(client, repo_dir, gate="uv run pytest")
    await _drive_to_closing(client, run_id)
    (repo_dir / "feature.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "closed"
    argv = _closer_argv(repo_dir)
    assert argv.startswith("t1 ")  # the run's work unit
    # The repo's own gate, wrapped so close_ticket runs it under the same
    # shell rules as the inline path.
    assert "--gate-command bash -lc 'uv run pytest'" in argv
    log = subprocess.run(
        ["git", "-C", str(repo_dir), "log", "--oneline"], capture_output=True, text=True
    )
    assert "t1" in log.stdout                        # committed after the closer
    event = await _gate_event(client, run_id)
    assert event["payload"]["gate_command"] == "uv run pytest"
    assert "close_ticket" in event["payload"]["summary"]


async def test_closer_refusal_surfaces_and_leaves_the_run_unclosed(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_closer(
        repo_dir, exit_code=1,
        stderr="Ticket is at Phase: green; close requires review-loop.",
    )
    run_id = await _run_on(client, repo_dir, gate="uv run pytest")
    await _drive_to_closing(client, run_id)
    (repo_dir / "feature.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_failed"
    assert "close requires review-loop" in event["payload"]["summary"]  # verbatim reason
    log = subprocess.run(
        ["git", "-C", str(repo_dir), "log", "--oneline"], capture_output=True, text=True
    )
    assert "t1" not in log.stdout  # nothing committed on refusal


async def test_slow_repo_closer_times_out_to_needs_work(
    db, client, tmp_path, monkeypatch
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_closer(repo_dir, delay_s=1)
    run_id = await _run_on(client, repo_dir, gate="true")
    await _drive_to_closing(client, run_id)
    monkeypatch.setattr(worker, "_TIMEOUT_S", 0.01)

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_failed"
    assert "timed out" in event["payload"]["summary"]


async def test_repo_closer_spawn_error_routes_to_needs_work(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_closer(repo_dir)
    (repo_dir / "scripts" / "close_ticket").chmod(0o644)
    run_id = await _run_on(client, repo_dir, gate="true")
    await _drive_to_closing(client, run_id)

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_failed"
    assert "could not start" in event["payload"]["summary"]


async def test_non_pass_review_tags_the_closer_refusal_as_a_verdict_failure(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_closer(
        repo_dir, exit_code=1,
        stderr="Reviewer verdict is needs-work; close requires pass.",
    )
    run_id = await _run_on(client, repo_dir, gate="uv run pytest")

    async def post(path, body):
        await client.post(
            f"/api/v1/runs/{run_id}{path}", json=body, headers=AUTH
        )

    await post("/claim", {"role": "builder", "holder": "codex"})
    await post("/events", {"type": "builder_brief_posted", "actor": "builder"})
    await post("/claim", {"role": "reviewer", "holder": "claude"})
    await post(
        "/events",
        {
            "type": "reviewer_findings_posted",
            "actor": "reviewer",
            "payload": {
                "verdict": "changes",
                "escalated": True,
                "summary": "worker.py:533 — preserve the located fix.",
            },
        },
    )
    await post("/decision", {"decision": "approve"})
    await post("/decision", {"decision": "close"})

    assert await run_pass(db, run_id, "closer", "system") == "done"

    event = await _gate_event(client, run_id)
    assert event["payload"]["failure_kind"] == "review_verdict"


async def test_ungated_repo_still_delegates_and_says_ungated(db, client, tmp_path):
    """close_ticket demands a gate command; a repo with none gets the no-op —
    and the run records that nothing was verified, exactly as the inline path
    does."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_closer(repo_dir)
    run_id = await _run_on(client, repo_dir)  # no gate registered
    await _drive_to_closing(client, run_id)
    (repo_dir / "feature.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "closed"
    assert "--gate-command bash -lc true" in _closer_argv(repo_dir)
    event = await _gate_event(client, run_id)
    assert event["payload"]["gate_command"] is None
    assert "ungated" in event["payload"]["summary"]
