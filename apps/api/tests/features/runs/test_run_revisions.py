"""The human-facing run history: reviewed checkpoints, not agent traffic."""

import json
import subprocess

from app.worker import _incremental_diff, _revision_base_content, run_pass
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


async def _run_on(client, repo_path, *, slug="revisions") -> int:
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": slug, "name": slug, "path": str(repo_path)},
        headers=AUTH,
    )).json()["id"]
    return (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo"},
        headers=AUTH,
    )).json()["id"]


async def _detail(client, run_id: int) -> dict:
    return (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()


async def _agent_loop(db, run_id: int) -> None:
    assert await run_pass(db, run_id, "builder", "stub") == "done"
    assert await run_pass(db, run_id, "reviewer", "stub") == "done"


async def _request_changes(client, run_id: int, note: str) -> None:
    response = await client.post(
        f"/api/v1/runs/{run_id}/decision",
        json={"decision": "request_changes", "note": note},
        headers=AUTH,
    )
    assert response.status_code == 200


async def test_initial_agent_loop_becomes_one_reviewed_checkpoint(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    await _agent_loop(db, run_id)

    detail = await _detail(client, run_id)
    assert len(detail["revisions"]) == 1
    revision = detail["revisions"][0]
    assert revision["request"] is None
    assert revision["headline"] == "stub builder pass complete"
    assert revision["diff"].count("+# built by stub agent") == 1


async def test_private_review_bounce_stays_inside_one_checkpoint(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    assert await run_pass(db, run_id, "builder", "stub") == "done"
    assert (await _detail(client, run_id))["revisions"] == []
    await client.post(
        f"/api/v1/runs/{run_id}/claim",
        json={"role": "reviewer", "holder": "stub"}, headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={
            "type": "reviewer_findings_posted", "actor": "reviewer",
            "payload": {"verdict": "changes", "summary": "tighten it"},
        },
        headers=AUTH,
    )

    await _agent_loop(db, run_id)

    revisions = (await _detail(client, run_id))["revisions"]
    assert len(revisions) == 1
    assert revisions[0]["diff"].count("+# built by stub agent") == 2


async def test_human_request_gets_only_the_incremental_response_diff(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    await _agent_loop(db, run_id)

    await _request_changes(client, run_id, "add three loading dots")
    pending = await _detail(client, run_id)
    assert pending["pending_revision_request"]["text"] == "add three loading dots"

    await _agent_loop(db, run_id)

    revisions = (await _detail(client, run_id))["revisions"]
    assert [revision["request"] for revision in revisions] == [
        None, "add three loading dots",
    ]
    assert revisions[0]["diff"].count("+# built by stub agent") == 1
    assert revisions[1]["diff"].count("+# built by stub agent") == 1
    artifacts = (await _detail(client, run_id))["artifacts"]
    full_candidate = next(
        artifact for artifact in reversed(artifacts) if artifact["kind"] == "diff"
    )
    assert full_candidate["content"].count("+# built by stub agent") == 2


async def test_repeated_requests_append_oldest_to_newest(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    await _agent_loop(db, run_id)
    await _request_changes(client, run_id, "add three loading dots")
    await _agent_loop(db, run_id)
    await _request_changes(client, run_id, "keep the dots still")
    await _agent_loop(db, run_id)

    revisions = (await _detail(client, run_id))["revisions"]
    assert [revision["request"] for revision in revisions] == [
        None, "add three loading dots", "keep the dots still",
    ]
    assert all(
        revision["diff"].count("+# built by stub agent") == 1
        for revision in revisions
    )


async def test_informational_note_does_not_start_a_revision(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    await _agent_loop(db, run_id)

    await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={
            "type": "human_note_posted", "actor": "human",
            "payload": {"note": "a thought, not a change request"},
        },
        headers=AUTH,
    )

    detail = await _detail(client, run_id)
    assert len(detail["revisions"]) == 1
    assert detail["pending_revision_request"] is None


async def test_legacy_run_falls_back_to_its_latest_summary_and_diff(client):
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "legacy", "name": "legacy", "path": "/p"},
        headers=AUTH,
    )).json()["id"]
    run_id = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "old", "title": "old run"},
        headers=AUTH,
    )).json()["id"]
    await client.post(
        f"/api/v1/runs/{run_id}/claim",
        json={"role": "builder", "holder": "old"}, headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/artifacts",
        json={"kind": "diff", "content": "legacy cumulative diff"}, headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={
            "type": "builder_brief_posted", "actor": "builder",
            "payload": {"summary": "legacy summary"},
        },
        headers=AUTH,
    )
    # A development-era raw baseline cannot safely replay after HEAD moves and
    # must not suppress the useful legacy fallback.
    await client.post(
        f"/api/v1/runs/{run_id}/artifacts",
        json={"kind": "revision_base", "content": "old cumulative patch"},
        headers=AUTH,
    )

    detail = await _detail(client, run_id)
    brief_event = next(
        event for event in detail["events"] if event["type"] == "builder_brief_posted"
    )
    assert detail["revisions"] == [{
        "checkpoint_event_id": brief_event["id"],
        "request_event_id": None,
        "request": None,
        "headline": "legacy summary",
        "diff": "legacy cumulative diff",
        "created_at": brief_event["created_at"],
    }]


async def test_persisted_builder_headline_is_the_projection_source(client):
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "headline", "name": "headline", "path": "/p"},
        headers=AUTH,
    )).json()["id"]
    run_id = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "old", "title": "old run"},
        headers=AUTH,
    )).json()["id"]
    await client.post(
        f"/api/v1/runs/{run_id}/claim",
        json={"role": "builder", "holder": "old"}, headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={
            "type": "builder_brief_posted", "actor": "builder",
            "payload": {
                "summary": "SUMMARY: reparsing this would be wrong",
                "headline": "persisted headline",
            },
        },
        headers=AUTH,
    )

    detail = await _detail(client, run_id)

    assert detail["revisions"][0]["headline"] == "persisted headline"


async def test_legacy_fallback_remains_when_its_first_new_revision_is_pending(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    await client.post(
        f"/api/v1/runs/{run_id}/claim",
        json={"role": "builder", "holder": "old"}, headers=AUTH,
    )
    (repo_dir / "legacy.py").write_text("VALUE = 1\n")
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)
    cumulative = subprocess.run(
        ["git", "-C", str(repo_dir), "diff", "--cached"],
        capture_output=True, text=True, check=True,
    ).stdout
    await client.post(
        f"/api/v1/runs/{run_id}/artifacts",
        json={"kind": "diff", "content": cumulative}, headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={
            "type": "builder_brief_posted", "actor": "builder",
            "payload": {"summary": "legacy result"},
        },
        headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/claim",
        json={"role": "reviewer", "holder": "old"}, headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={
            "type": "reviewer_findings_posted", "actor": "reviewer",
            "payload": {"verdict": "pass"},
        },
        headers=AUTH,
    )
    await _request_changes(client, run_id, "modern revision")

    assert await run_pass(db, run_id, "builder", "stub") == "done"
    pending = await _detail(client, run_id)
    assert [revision["headline"] for revision in pending["revisions"]] == [
        "legacy result"
    ]
    assert pending["pending_revision_request"]["text"] == "modern revision"

    assert await run_pass(db, run_id, "reviewer", "stub") == "done"
    complete = await _detail(client, run_id)
    assert [revision["request"] for revision in complete["revisions"]] == [
        None, "modern revision",
    ]


def test_incremental_baseline_survives_head_moving_during_the_agent_pass(tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    feature = repo_dir / "feature.py"
    feature.write_text("A = 1\n")
    baseline = _revision_base_content(str(repo_dir))
    assert set(json.loads(baseline)) == {"version", "tree"}

    subprocess.run(
        [
            "git", "-C", str(repo_dir), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-q", "-m", "concurrent baseline",
        ],
        check=True,
    )
    feature.write_text("A = 1\nB = 2\n")
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)

    incremental = _incremental_diff(str(repo_dir), baseline)

    assert "+B = 2" in incremental
    assert "+A = 1" not in incremental
