"""The close gate belongs to the repo (acp-015): each registered repository
carries its own close-gate command. Registration suggests the repo's documented
test command where one is discoverable — and never invents one."""

from app.config import settings
from tests.conftest import AUTH


def _git_dir(root, name: str):
    d = root / name
    (d / ".git").mkdir(parents=True)
    return d


async def test_register_accepts_a_close_gate_command(client):
    resp = await client.post(
        "/api/v1/repos",
        json={"slug": "gated", "name": "Gated", "path": "/nowhere/gated",
              "close_gate_command": "uv run pytest"},
        headers=AUTH,
    )
    assert resp.status_code == 201
    assert resp.json()["close_gate_command"] == "uv run pytest"


async def test_register_without_a_discoverable_command_stays_ungated(client):
    """No Makefile, no package.json — nothing documented means nothing invented."""
    resp = await client.post(
        "/api/v1/repos",
        json={"slug": "bare", "name": "Bare", "path": "/nowhere/bare"},
        headers=AUTH,
    )
    assert resp.json()["close_gate_command"] is None


async def test_scan_suggests_make_test_from_the_repos_makefile(
    db, client, tmp_path, monkeypatch
):
    repo = _git_dir(tmp_path, "maked")
    (repo / "Makefile").write_text("install:\n\tuv sync\n\ntest:\n\tpytest\n")
    monkeypatch.setattr(settings, "projects_root", str(tmp_path))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert repos[0]["close_gate_command"] == "make test"


async def test_scan_suggests_npm_test_from_package_json(db, client, tmp_path, monkeypatch):
    repo = _git_dir(tmp_path, "noded")
    (repo / "package.json").write_text('{"scripts": {"test": "vitest run"}}')
    monkeypatch.setattr(settings, "projects_root", str(tmp_path))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert repos[0]["close_gate_command"] == "npm test"


async def test_scan_never_invents_a_gate(db, client, tmp_path, monkeypatch):
    repo = _git_dir(tmp_path, "plain")
    (repo / "Makefile").write_text("serve:\n\tuvicorn app.main:app\n")
    monkeypatch.setattr(settings, "projects_root", str(tmp_path))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert repos[0]["close_gate_command"] is None


async def test_sync_never_clobbers_a_repos_gate(db, client, tmp_path, monkeypatch):
    """A rescan must not overwrite the gate — not even with a fresh suggestion:
    a human who cleared or customised it has spoken."""
    repo = _git_dir(tmp_path, "kept")
    (repo / "Makefile").write_text("test:\n\tpytest\n")
    monkeypatch.setattr(settings, "projects_root", str(tmp_path))
    repo_id = (await client.get("/api/v1/repos", headers=AUTH)).json()[0]["id"]

    await client.put(f"/api/v1/repos/{repo_id}/gate",
                     json={"close_gate_command": "uv run pytest -x"}, headers=AUTH)
    after = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert after[0]["close_gate_command"] == "uv run pytest -x"


async def test_edit_sets_and_clears_the_gate(client):
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "edited", "name": "Edited", "path": "/nowhere/edited"},
        headers=AUTH,
    )).json()["id"]

    setr = await client.put(f"/api/v1/repos/{repo_id}/gate",
                            json={"close_gate_command": "make test"}, headers=AUTH)
    assert setr.status_code == 200
    assert setr.json()["close_gate_command"] == "make test"

    clear = await client.put(f"/api/v1/repos/{repo_id}/gate",
                             json={"close_gate_command": None}, headers=AUTH)
    assert clear.json()["close_gate_command"] is None


async def test_blank_gate_command_is_no_gate(client):
    """`bash -lc ""` exits 0 — whitespace would be a gate that verifies nothing
    while looking configured. Normalise it to ungated."""
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "blank", "name": "Blank", "path": "/nowhere/blank"},
        headers=AUTH,
    )).json()["id"]

    resp = await client.put(f"/api/v1/repos/{repo_id}/gate",
                            json={"close_gate_command": "   "}, headers=AUTH)

    assert resp.json()["close_gate_command"] is None


async def test_edit_unknown_repo_is_404(client):
    resp = await client.put("/api/v1/repos/999999/gate",
                            json={"close_gate_command": "make test"}, headers=AUTH)
    assert resp.status_code == 404
