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
