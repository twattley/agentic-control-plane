"""Ticket 022: a builder must not author the verdict that closes its ticket.

The prompt half is pinned in test_task_spec. This file pins the detection
half: a builder pass that commits under the worker (moved HEAD) is recorded
on the run as a visible event, and a clean pass is not.
"""

from app import worker
from app.worker import run_pass
from tests.conftest import AUTH
from tests.features.runs.test_dispatch import _git_repo, _run_on

_ROGUE = [
    "bash", "-c",
    "echo rogue >> README.md && git add -A && "
    "git -c user.email=r@r -c user.name=r commit -qm rogue",
]


async def test_builder_pass_that_commits_is_flagged(db, client, tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    monkeypatch.setattr(worker, "_agent_command", lambda role, provider, task, path: _ROGUE)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    flagged = [e for e in detail["events"] if e["type"] == "builder_committed"]
    assert len(flagged) == 1
    assert flagged[0]["payload"]["head_before"] != flagged[0]["payload"]["head_after"]
    assert flagged[0]["payload"]["summary"]
    # informational: the run still flows to review, nothing is silently absorbed
    assert detail["run"]["state"] == "awaiting_review"
    assert any(e["type"] == "builder_brief_posted" for e in detail["events"])


async def test_clean_builder_pass_is_not_flagged(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    assert not [e for e in detail["events"] if e["type"] == "builder_committed"]
