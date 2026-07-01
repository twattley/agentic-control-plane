import subprocess

from app.worker import run_pass
from tests.conftest import AUTH


def _git_repo(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README.md").write_text("# repo\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init"],
        check=True,
    )


async def _run_on(client, repo_path) -> int:
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "tmp", "name": "tmp", "path": str(repo_path)},
        headers=AUTH,
    )).json()["id"]
    return (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo"},
        headers=AUTH,
    )).json()["id"]


async def test_stub_builder_pass_produces_diff_and_advances(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    assert detail["run"]["state"] == "awaiting_review"
    assert any(a["kind"] == "diff" for a in detail["artifacts"])
    assert "AGENT_LOG.md" in next(a["content"] for a in detail["artifacts"] if a["kind"] == "diff")


async def test_second_builder_pass_is_skipped(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    assert await run_pass(db, run_id, "builder", "stub") == "done"
    # run is now awaiting_review — a re-fired builder loses the claim race
    assert await run_pass(db, run_id, "builder", "stub") == "skipped"


async def _drive_to_closing(client, run_id: int) -> None:
    async def post(path, body):
        await client.post(f"/api/v1/runs/{run_id}{path}", json=body, headers=AUTH)
    await post("/claim", {"role": "builder", "holder": "codex"})
    await post("/events", {"type": "builder_brief_posted", "actor": "builder"})
    await post("/claim", {"role": "reviewer", "holder": "claude"})
    await post("/events", {"type": "reviewer_findings_posted", "actor": "reviewer", "payload": {"verdict": "pass"}})
    await post("/decision", {"decision": "approve"})
    await post("/decision", {"decision": "close"})


async def _state(client, run_id: int) -> str:
    return (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()["run"]["state"]


async def test_closer_gate_pass_commits_and_closes(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    await _drive_to_closing(client, run_id)
    assert await _state(client, run_id) == "closing"

    # an agent-made change sitting uncommitted in the checkout
    (repo_dir / "feature.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"
    assert await _state(client, run_id) == "closed"
    log = subprocess.run(["git", "-C", str(repo_dir), "log", "--oneline"], capture_output=True, text=True)
    assert "t1" in log.stdout  # ticket id landed in the commit message


async def test_closer_gate_fail_routes_to_needs_work(db, client, tmp_path, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "close_gate_command", "exit 1")  # gate fails
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    await _drive_to_closing(client, run_id)

    assert await run_pass(db, run_id, "closer", "system") == "done"
    assert await _state(client, run_id) == "needs_work"
