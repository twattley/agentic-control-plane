import subprocess

from app import worker
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


async def _run_on(client, repo_path, *, slug="tmp", ticket="t1", gate=None) -> int:
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": slug, "name": slug, "path": str(repo_path),
              "close_gate_command": gate},
        headers=AUTH,
    )).json()["id"]
    return (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": ticket, "title": "demo"},
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
    await post("/events", {"type": "reviewer_findings_posted", "actor": "reviewer",
                           "payload": {"verdict": "pass"}})
    await post("/decision", {"decision": "approve"})
    await post("/decision", {"decision": "close"})


async def _state(client, run_id: int) -> str:
    return (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()["run"]["state"]


async def _gate_event(client, run_id: int) -> dict:
    events = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()["events"]
    return next(e for e in reversed(events) if e["type"] in ("gate_passed", "gate_failed"))


async def test_closer_runs_the_repos_own_gate_and_closes(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    # only this checkout satisfies the gate — proves it ran in the run's repo
    run_id = await _run_on(client, repo_dir, gate="test -f README.md")
    await _drive_to_closing(client, run_id)
    assert await _state(client, run_id) == "closing"

    # an agent-made change sitting uncommitted in the checkout
    (repo_dir / "feature.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"
    assert await _state(client, run_id) == "closed"
    log = subprocess.run(
        ["git", "-C", str(repo_dir), "log", "--oneline"], capture_output=True, text=True
    )
    assert "t1" in log.stdout  # ticket id landed in the commit message

    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_passed"
    assert event["payload"]["gate_command"] == "test -f README.md"


async def test_closer_gate_fail_routes_to_needs_work(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir, gate="exit 1")
    await _drive_to_closing(client, run_id)

    assert await run_pass(db, run_id, "closer", "system") == "done"
    assert await _state(client, run_id) == "needs_work"
    assert (await _gate_event(client, run_id))["payload"]["gate_command"] == "exit 1"


async def test_slow_inline_gate_times_out_to_needs_work(
    db, client, tmp_path, monkeypatch
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir, gate="sleep 1")
    await _drive_to_closing(client, run_id)
    monkeypatch.setattr(worker, "_TIMEOUT_S", 0.01)

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_failed"
    assert "timed out" in event["payload"]["summary"]


async def test_inline_gate_spawn_error_routes_to_needs_work(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir, gate="true")
    await _drive_to_closing(client, run_id)
    repo_dir.rename(tmp_path / "unavailable-repo")

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_failed"
    assert "could not start" in event["payload"]["summary"]


async def test_ungated_close_closes_and_says_so(db, client, tmp_path):
    """No gate is allowed — but it is a recorded fact about the run, never a
    silent default the view could mistake for a verified close."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)  # registered with no gate
    await _drive_to_closing(client, run_id)
    (repo_dir / "feature.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"
    assert await _state(client, run_id) == "closed"

    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_passed"
    assert event["payload"]["gate_command"] is None
    assert "ungated" in event["payload"]["summary"]


async def test_two_repos_close_on_their_own_gates_in_one_service(db, client, tmp_path):
    """Done-when: different gate commands both close correctly with nothing
    reconfigured between them — the seam the global setting made impossible."""
    dir_a, dir_b = tmp_path / "repo-a", tmp_path / "repo-b"
    _git_repo(dir_a)
    _git_repo(dir_b)
    (dir_a / "a.marker").write_text("")
    (dir_b / "b.marker").write_text("")
    run_a = await _run_on(client, dir_a, slug="repo-a", ticket="ta", gate="test -f a.marker")
    run_b = await _run_on(client, dir_b, slug="repo-b", ticket="tb", gate="test -f b.marker")
    await _drive_to_closing(client, run_a)
    await _drive_to_closing(client, run_b)

    assert await run_pass(db, run_a, "closer", "system") == "done"
    assert await run_pass(db, run_b, "closer", "system") == "done"

    assert await _state(client, run_a) == "closed"
    assert await _state(client, run_b) == "closed"
