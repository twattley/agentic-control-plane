"""Agent-declared blockers leave the automatic builder/reviewer loop."""

import sys

from app import worker
from app.worker import run_pass
from tests.conftest import AUTH
from tests.features.runs.test_dispatch import _git_repo, _run_on, _state


def _blocked_agent_command(captured_tasks):
    def command(_role, _provider, task, _repo_path):
        captured_tasks.append(task)
        return [
            sys.executable,
            "-c",
            "print('SUMMARY: dependency missing\\nDISPOSITION: blocked')",
        ]

    return command


def _blocked_reviewer_command(captured_tasks):
    def command(_role, _provider, task, _repo_path):
        captured_tasks.append(task)
        return [
            sys.executable,
            "-c",
            (
                "print('Blocking dependency confirmed\\n"
                "DISPOSITION: blocked\\nVERDICT: changes')"
            ),
        ]

    return command


async def test_builder_blocked_disposition_routes_directly_to_the_human(
    db, client, tmp_path, monkeypatch
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    captured_tasks = []
    dispatched_states = []
    monkeypatch.setattr(worker, "_agent_command", _blocked_agent_command(captured_tasks))
    monkeypatch.setattr(
        worker.executor,
        "maybe_dispatch",
        lambda _run, state: dispatched_states.append(state),
    )

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    brief = next(
        event for event in detail["events"] if event["type"] == "builder_brief_posted"
    )
    assert await _state(client, run_id) == "awaiting_human"
    assert brief["payload"]["disposition"] == "blocked"
    assert dispatched_states == ["awaiting_human"]
    assert "DISPOSITION: blocked" in captured_tasks[0]


async def test_reviewer_blocked_disposition_does_not_return_to_the_builder(
    db, client, tmp_path, monkeypatch
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    async def post(path, body):
        response = await client.post(
            f"/api/v1/runs/{run_id}{path}", json=body, headers=AUTH
        )
        assert 200 <= response.status_code < 300

    await post("/claim", {"role": "builder", "holder": "codex"})
    await post(
        "/events",
        {
            "type": "builder_brief_posted",
            "actor": "builder",
            "payload": {"summary": "Blocked by an unmet dependency."},
        },
    )

    captured_tasks = []
    dispatched_states = []
    monkeypatch.setattr(
        worker, "_agent_command", _blocked_reviewer_command(captured_tasks)
    )
    monkeypatch.setattr(
        worker.executor,
        "maybe_dispatch",
        lambda _run, state: dispatched_states.append(state),
    )

    assert await run_pass(db, run_id, "reviewer", "stub") == "done"

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    findings = next(
        event
        for event in detail["events"]
        if event["type"] == "reviewer_findings_posted"
    )
    assert await _state(client, run_id) == "awaiting_human"
    assert findings["payload"]["disposition"] == "blocked"
    assert findings["payload"]["verdict"] == "changes"
    assert dispatched_states == ["awaiting_human"]
    assert "DISPOSITION: blocked" in captured_tasks[0]
