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


async def _claim(client, run_id: int, role: str, holder: str):
    return await client.post(
        f"/api/v1/runs/{run_id}/claim",
        json={"role": role, "holder": holder}, headers=AUTH,
    )


async def _event(client, run_id: int, type_: str, actor: str, **payload):
    return await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={"type": type_, "actor": actor, "payload": payload}, headers=AUTH,
    )


async def _decide(client, run_id: int, decision: str, **extra):
    return await client.post(
        f"/api/v1/runs/{run_id}/decision",
        json={"decision": decision, **extra}, headers=AUTH,
    )


async def _queue(client, name: str) -> list[int]:
    q = (await client.get(f"/api/v1/queue/{name}", headers=AUTH)).json()
    return [r["id"] for r in q]


async def test_new_run_starts_queued_with_created_event(client):
    run_id = await _run(client)
    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    assert detail["run"]["state"] == "queued"
    assert [e["type"] for e in detail["events"]] == ["run_created"]


async def test_full_happy_path_to_closed(client):
    run_id = await _run(client)

    # builder claims -> building
    await _claim(client, run_id, "builder", "codex")
    assert await _state(client, run_id) == "building"

    # builder posts brief -> awaiting_review, attaches diff
    await _event(client, run_id, "builder_brief_posted", "builder")
    assert await _state(client, run_id) == "awaiting_review"
    await client.post(
        f"/api/v1/runs/{run_id}/artifacts",
        json={"kind": "diff", "content": "diff --git ..."}, headers=AUTH,
    )

    assert await _queue(client, "review") == [run_id]

    # reviewer claims -> reviewing, requests changes -> needs_work
    await _claim(client, run_id, "reviewer", "claude")
    await _event(
        client, run_id, "reviewer_findings_posted", "reviewer", verdict="changes"
    )
    assert await _state(client, run_id) == "needs_work"

    assert await _queue(client, "fix") == [run_id]

    # builder fixes -> fixing -> awaiting_review; reviewer passes -> awaiting_human
    await _claim(client, run_id, "builder", "codex")
    assert await _state(client, run_id) == "fixing"
    await _event(client, run_id, "builder_brief_posted", "builder")
    await _claim(client, run_id, "reviewer", "claude")
    await _event(
        client, run_id, "reviewer_findings_posted", "reviewer", verdict="pass"
    )
    assert await _state(client, run_id) == "awaiting_human"

    assert await _queue(client, "human") == [run_id]

    # human approves -> approved -> closing (closer worker gates+commits) -> closed
    await _decide(client, run_id, "approve")
    assert await _state(client, run_id) == "approved"
    await _decide(client, run_id, "close")
    assert await _state(client, run_id) == "closing"
    # the closer reports the gate passed
    await _event(client, run_id, "gate_passed", "system")
    assert await _state(client, run_id) == "closed"


async def test_illegal_transition_is_409(client):
    run_id = await _run(client)
    # reviewer cannot claim a queued run
    assert (await _claim(client, run_id, "reviewer", "claude")).status_code == 409
    # cannot approve a queued run
    assert (await _decide(client, run_id, "approve")).status_code == 409


async def test_double_builder_claim_conflicts(client):
    run_id = await _run(client)
    await _claim(client, run_id, "builder", "codex")
    # second builder claim: illegal transition (building has no builder-claim edge)
    assert (await _claim(client, run_id, "builder", "codex")).status_code == 409


async def test_missing_run_is_404(client):
    r = await client.get("/api/v1/runs/999999", headers=AUTH)
    assert r.status_code == 404


async def test_block_from_active_state(client):
    run_id = await _run(client)
    await _claim(client, run_id, "builder", "codex")
    r = await _decide(client, run_id, "block", note="waiting on infra")
    assert r.status_code == 200
    assert await _state(client, run_id) == "blocked"
