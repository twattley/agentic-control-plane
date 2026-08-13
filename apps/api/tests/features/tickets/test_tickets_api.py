from tests.conftest import AUTH


async def _register(client, path: str) -> int:
    resp = await client.post(
        "/api/v1/repos",
        json={"slug": "t", "name": "T", "path": path},
        headers=AUTH,
    )
    return resp.json()["id"]


def _make_tickets(tmp_path):
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "ACP-2.md").write_text("# Add the frobnicator\n\nDetails here.\n")
    (tickets / "ACP-10.md").write_text("no heading, just prose\n")
    (tickets / "notes.txt").write_text("not a ticket")
    return tickets


async def test_list_tickets_returns_md_files_with_titles(client, tmp_path):
    _make_tickets(tmp_path)
    repo_id = await _register(client, str(tmp_path))

    resp = await client.get(f"/api/v1/repos/{repo_id}/tickets", headers=AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert [t["slug"] for t in body] == ["ACP-10", "ACP-2"]
    by_slug = {t["slug"]: t for t in body}
    assert by_slug["ACP-2"]["title"] == "Add the frobnicator"
    assert by_slug["ACP-10"]["title"] == "ACP-10"  # no heading -> slug


async def test_list_tickets_no_folder_is_empty(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))
    resp = await client.get(f"/api/v1/repos/{repo_id}/tickets", headers=AUTH)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_tickets_unknown_repo_404(client):
    resp = await client.get("/api/v1/repos/999/tickets", headers=AUTH)
    assert resp.status_code == 404


async def test_get_ticket_returns_content(client, tmp_path):
    _make_tickets(tmp_path)
    repo_id = await _register(client, str(tmp_path))

    resp = await client.get(f"/api/v1/repos/{repo_id}/tickets/ACP-2", headers=AUTH)

    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "ACP-2"
    assert body["title"] == "Add the frobnicator"
    assert "Details here." in body["content"]


async def test_get_ticket_missing_404(client, tmp_path):
    _make_tickets(tmp_path)
    repo_id = await _register(client, str(tmp_path))
    resp = await client.get(f"/api/v1/repos/{repo_id}/tickets/ACP-99", headers=AUTH)
    assert resp.status_code == 404


async def test_get_ticket_rejects_path_traversal(client, tmp_path):
    _make_tickets(tmp_path)
    (tmp_path / "secret.md").write_text("# secret")
    repo_id = await _register(client, str(tmp_path))

    resp = await client.get(
        f"/api/v1/repos/{repo_id}/tickets/..%2Fsecret", headers=AUTH
    )

    assert resp.status_code == 404


async def test_tickets_require_token(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))
    resp = await client.get(f"/api/v1/repos/{repo_id}/tickets")
    assert resp.status_code == 401
