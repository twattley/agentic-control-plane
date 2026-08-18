"""A dead agent process leaves a visible, actionable run behind."""

import pytest

from app import worker
from tests.conftest import AUTH
from tests.features.runs.test_dispatch import _git_repo, _run_on


@pytest.mark.parametrize(
    ("waiting_state", "role", "active_state"),
    [
        ("queued", "builder", "building"),
        ("needs_work", "builder", "fixing"),
        ("awaiting_review", "reviewer", "reviewing"),
    ],
)
async def test_post_claim_failure_returns_the_run_to_the_human(
    db, client, tmp_path, monkeypatch, waiting_state, role, active_state
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    async def post(path: str, body: dict):
        response = await client.post(
            f"/api/v1/runs/{run_id}{path}", json=body, headers=AUTH
        )
        assert 200 <= response.status_code < 300

    if waiting_state in {"needs_work", "awaiting_review"}:
        await post("/claim", {"role": "builder", "holder": "old-builder"})
        await post(
            "/events", {"type": "builder_brief_posted", "actor": "builder"}
        )
    if waiting_state == "needs_work":
        await post("/claim", {"role": "reviewer", "holder": "old-reviewer"})
        await post(
            "/events",
            {
                "type": "reviewer_findings_posted",
                "actor": "reviewer",
                "payload": {"verdict": "changes"},
            },
        )

    def fail_after_claim(*_args) -> list[str]:
        raise RuntimeError(f"agent exploded in {active_state}")

    monkeypatch.setattr(worker, "_agent_command", fail_after_claim)

    with pytest.raises(RuntimeError, match=f"agent exploded in {active_state}"):
        await worker.run_pass(db, run_id, role, "stub")

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    failure = detail["events"][-1]
    assert failure["type"] == "worker_failed"
    assert failure["actor"] == role
    assert failure["payload"] == {
        "role": role,
        "provider": "stub",
        "error": f"RuntimeError: agent exploded in {active_state}",
    }
    assert detail["run"]["state"] == "awaiting_human"
    assert detail["leases"][-1]["released_at"] is not None

    human_queue = (await client.get("/api/v1/queue/human", headers=AUTH)).json()
    assert [item["run"]["id"] for item in human_queue] == [run_id]
