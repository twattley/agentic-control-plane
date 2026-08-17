"""Outside checkout changes between agent passes remain visible on the run."""

import subprocess

from app.worker import run_pass
from tests.conftest import AUTH


def _git_repo(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README.md").write_text("# repo\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(
        [
            "git", "-C", str(path), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-q", "-m", "init",
        ],
        check=True,
    )


async def _run_on(client, repo_path) -> int:
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "external-edits", "name": "external-edits", "path": str(repo_path)},
        headers=AUTH,
    )).json()["id"]
    return (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo"},
        headers=AUTH,
    )).json()["id"]


async def _detail(client, run_id: int) -> dict:
    return (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()


async def test_first_pass_has_no_prior_checkout_to_flag(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    events = (await _detail(client, run_id))["events"]
    assert not [event for event in events if event["type"] == "external_edits_detected"]


async def test_commit_between_passes_is_flagged_before_the_next_agent_output(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    assert await run_pass(db, run_id, "builder", "stub") == "done"
    subprocess.run(
        [
            "git", "-C", str(repo_dir), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-q", "-am", "outside edit",
        ],
        check=True,
    )

    assert await run_pass(db, run_id, "reviewer", "stub") == "done"

    events = (await _detail(client, run_id))["events"]
    flagged = [event for event in events if event["type"] == "external_edits_detected"]
    assert len(flagged) == 1
    assert flagged[0]["payload"]["head_before"] != flagged[0]["payload"]["head_after"]
    assert flagged[0]["payload"]["summary"]
    assert events.index(flagged[0]) < next(
        index for index, event in enumerate(events)
        if event["type"] == "reviewer_findings_posted"
    )


async def test_working_tree_edit_between_passes_is_flagged(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    assert await run_pass(db, run_id, "builder", "stub") == "done"
    (repo_dir / "outside.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "reviewer", "stub") == "done"

    events = (await _detail(client, run_id))["events"]
    flagged = [event for event in events if event["type"] == "external_edits_detected"]
    assert len(flagged) == 1
    assert flagged[0]["payload"]["head_before"] != flagged[0]["payload"]["head_after"]
    assert (await _detail(client, run_id))["run"]["state"] == "awaiting_human"


async def test_undisturbed_checkout_is_not_flagged_and_reaches_the_same_state(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    assert await run_pass(db, run_id, "builder", "stub") == "done"

    assert await run_pass(db, run_id, "reviewer", "stub") == "done"

    detail = await _detail(client, run_id)
    assert not [
        event for event in detail["events"]
        if event["type"] == "external_edits_detected"
    ]
    assert detail["run"]["state"] == "awaiting_human"
