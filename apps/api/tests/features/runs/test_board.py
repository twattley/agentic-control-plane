"""The workbench board: one pane per active run — repo name, frozen ticket
summary, and the last event, in a single payload."""

from tests.conftest import AUTH


async def _repo_with_ticket(client, tmp_path) -> int:
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "T-1.md").write_text(
        "# Do the thing\n\n## Summary\n\nSwap the widget for a gadget without breaking the API.\n"
    )
    resp = await client.post(
        "/api/v1/repos",
        json={"slug": "proj", "name": "Proj", "path": str(tmp_path)},
        headers=AUTH,
    )
    return resp.json()["id"]


async def _run(client, repo_id: int, ticket_id: str = "T-1") -> int:
    resp = await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": ticket_id, "title": "Do the thing"},
        headers=AUTH,
    )
    return resp.json()["id"]


async def test_board_pane_has_repo_summary_and_last_event(db, client, tmp_path):
    repo_id = await _repo_with_ticket(client, tmp_path)
    run_id = await _run(client, repo_id)
    await client.post(f"/api/v1/runs/{run_id}/claim",
                      json={"role": "builder", "holder": "claude:sonnet"}, headers=AUTH)

    panes = (await client.get("/api/v1/board", headers=AUTH)).json()

    assert len(panes) == 1
    pane = panes[0]
    assert pane["repo_name"] == "Proj"
    assert pane["run"]["state"] == "building"
    assert pane["summary"] == "Swap the widget for a gadget without breaking the API."
    assert pane["last_event"]["type"] == "builder_claimed"


async def test_board_excludes_finished_runs(db, client, tmp_path):
    repo_id = await _repo_with_ticket(client, tmp_path)
    active = await _run(client, repo_id, "T-1")
    stopped = await _run(client, repo_id, "T-2")
    await client.post(f"/api/v1/runs/{stopped}/decision",
                      json={"decision": "block"}, headers=AUTH)

    panes = (await client.get("/api/v1/board", headers=AUTH)).json()

    assert [p["run"]["id"] for p in panes] == [active]


async def test_board_summary_is_null_without_a_ticket_file(db, client, tmp_path):
    repo_id = await _repo_with_ticket(client, tmp_path)
    await _run(client, repo_id, "T-9")  # no tickets/T-9.md

    panes = (await client.get("/api/v1/board", headers=AUTH)).json()

    assert panes[0]["summary"] is None
