"""The one write surface: creating and editing markdown files in tickets/.
The plane still never touches anything else in a checkout."""

from tests.conftest import AUTH


async def _register(client, path: str) -> int:
    resp = await client.post(
        "/api/v1/repos", json={"slug": "t", "name": "T", "path": path}, headers=AUTH
    )
    return resp.json()["id"]


async def test_create_ticket_writes_the_file(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/tickets",
        json={"slug": "T-1", "content": "# Do a thing\n\n## Summary\n\nSmall but real.\n"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    assert resp.json()["slug"] == "T-1"
    assert resp.json()["title"] == "Do a thing"
    assert (tmp_path / "tickets" / "T-1.md").read_text().startswith("# Do a thing")


async def test_create_makes_the_tickets_folder_if_missing(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))
    assert not (tmp_path / "tickets").exists()

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/tickets",
        json={"slug": "T-1", "content": "# x\n"}, headers=AUTH,
    )

    assert resp.status_code == 201


async def test_create_conflicts_if_ticket_exists(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "T-1.md").write_text("# already here\n")

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/tickets",
        json={"slug": "T-1", "content": "# clobber\n"}, headers=AUTH,
    )

    assert resp.status_code == 409
    assert (tmp_path / "tickets" / "T-1.md").read_text() == "# already here\n"


async def test_update_overwrites_existing_ticket(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "T-1.md").write_text("# v1\n")

    resp = await client.put(
        f"/api/v1/repos/{repo_id}/tickets/T-1",
        json={"content": "# v2\n\n## Summary\n\nSharper now.\n"}, headers=AUTH,
    )

    assert resp.status_code == 200
    assert resp.json()["summary"] == "Sharper now."
    assert (tmp_path / "tickets" / "T-1.md").read_text().startswith("# v2")


async def test_update_missing_ticket_404(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))
    resp = await client.put(
        f"/api/v1/repos/{repo_id}/tickets/T-9", json={"content": "# x\n"}, headers=AUTH
    )
    assert resp.status_code == 404


async def test_write_rejects_bad_slugs(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))

    for slug in ["../escape", "a/b", "a\\b", ".hidden", ""]:
        resp = await client.post(
            f"/api/v1/repos/{repo_id}/tickets",
            json={"slug": slug, "content": "# x\n"}, headers=AUTH,
        )
        assert resp.status_code in (404, 422), slug
    assert not (tmp_path / "escape.md").exists()
    assert not (tmp_path.parent / "escape.md").exists()


async def test_write_requires_token(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/tickets", json={"slug": "T-1", "content": "# x\n"}
    )
    assert resp.status_code == 401
