from tests.conftest import AUTH


async def _repo(client) -> int:
    r = await client.post(
        "/api/v1/repos",
        json={"slug": "racing-platform", "name": "Racing", "path": "/p"},
        headers=AUTH,
    )
    return r.json()["id"]


async def _run(client) -> int:
    repo_id = await _repo(client)
    r = await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "077-agent-handoff-api", "title": "Handoff API"},
        headers=AUTH,
    )
    return r.json()["id"]


async def _state(client, run_id: int) -> str:
    r = await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)
    return r.json()["run"]["state"]


async def test_new_run_starts_queued_with_created_event(client):
    run_id = await _run(client)
    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    assert detail["run"]["state"] == "queued"
    assert [e["type"] for e in detail["events"]] == ["run_created"]


async def test_full_happy_path_to_closed(client):
    run_id = await _run(client)

    # builder claims -> building
    await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "builder", "holder": "codex"}, headers=AUTH)
    assert await _state(client, run_id) == "building"

    # builder posts brief -> awaiting_review, attaches diff
    await client.post(f"/api/v1/runs/{run_id}/events", json={"type": "builder_brief_posted", "actor": "builder"}, headers=AUTH)
    assert await _state(client, run_id) == "awaiting_review"
    await client.post(f"/api/v1/runs/{run_id}/artifacts", json={"kind": "diff", "content": "diff --git ..."}, headers=AUTH)

    # in review queue
    q = (await client.get("/api/v1/queue/review", headers=AUTH)).json()
    assert [r["id"] for r in q] == [run_id]

    # reviewer claims -> reviewing, requests changes -> needs_work
    await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "reviewer", "holder": "claude"}, headers=AUTH)
    await client.post(f"/api/v1/runs/{run_id}/events", json={"type": "reviewer_findings_posted", "actor": "reviewer", "payload": {"verdict": "changes"}}, headers=AUTH)
    assert await _state(client, run_id) == "needs_work"

    # in fix queue
    q = (await client.get("/api/v1/queue/fix", headers=AUTH)).json()
    assert [r["id"] for r in q] == [run_id]

    # builder fixes -> fixing -> awaiting_review; reviewer passes -> awaiting_human
    await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "builder", "holder": "codex"}, headers=AUTH)
    assert await _state(client, run_id) == "fixing"
    await client.post(f"/api/v1/runs/{run_id}/events", json={"type": "builder_brief_posted", "actor": "builder"}, headers=AUTH)
    await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "reviewer", "holder": "claude"}, headers=AUTH)
    await client.post(f"/api/v1/runs/{run_id}/events", json={"type": "reviewer_findings_posted", "actor": "reviewer", "payload": {"verdict": "pass"}}, headers=AUTH)
    assert await _state(client, run_id) == "awaiting_human"

    # in human queue
    q = (await client.get("/api/v1/queue/human", headers=AUTH)).json()
    assert [r["id"] for r in q] == [run_id]

    # human approves -> approved -> closing (closer worker gates+commits) -> closed
    await client.post(f"/api/v1/runs/{run_id}/decision", json={"decision": "approve"}, headers=AUTH)
    assert await _state(client, run_id) == "approved"
    await client.post(f"/api/v1/runs/{run_id}/decision", json={"decision": "close"}, headers=AUTH)
    assert await _state(client, run_id) == "closing"
    # the closer reports the gate passed
    await client.post(f"/api/v1/runs/{run_id}/events", json={"type": "gate_passed", "actor": "system"}, headers=AUTH)
    assert await _state(client, run_id) == "closed"


async def test_illegal_transition_is_409(client):
    run_id = await _run(client)
    # reviewer cannot claim a queued run
    r = await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "reviewer", "holder": "claude"}, headers=AUTH)
    assert r.status_code == 409
    # cannot approve a queued run
    r = await client.post(f"/api/v1/runs/{run_id}/decision", json={"decision": "approve"}, headers=AUTH)
    assert r.status_code == 409


async def test_double_builder_claim_conflicts(client):
    run_id = await _run(client)
    await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "builder", "holder": "codex"}, headers=AUTH)
    # second builder claim: illegal transition (building has no builder-claim edge)
    r = await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "builder", "holder": "codex"}, headers=AUTH)
    assert r.status_code == 409


async def test_missing_run_is_404(client):
    r = await client.get("/api/v1/runs/999999", headers=AUTH)
    assert r.status_code == 404


async def test_block_from_active_state(client):
    run_id = await _run(client)
    await client.post(f"/api/v1/runs/{run_id}/claim", json={"role": "builder", "holder": "codex"}, headers=AUTH)
    r = await client.post(f"/api/v1/runs/{run_id}/decision", json={"decision": "block", "note": "waiting on infra"}, headers=AUTH)
    assert r.status_code == 200
    assert await _state(client, run_id) == "blocked"
