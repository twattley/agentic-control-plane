"""Projects register themselves: GET /repos scans the projects root, upserts
every git repo found, and lists only repos that really exist under the root."""

from app.config import settings
from tests.conftest import AUTH


def _root_with(tmp_path, *, git: list[str] = (), plain: list[str] = ()):
    for name in git:
        (tmp_path / name / ".git").mkdir(parents=True)
    for name in plain:
        (tmp_path / name).mkdir(parents=True)
    return tmp_path


async def test_git_dirs_auto_register_with_pretty_names(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["my-cool-app"], plain=["notes", ".hidden"])
    monkeypatch.setattr(settings, "projects_root", str(root))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert [r["slug"] for r in repos] == ["my-cool-app"]
    assert repos[0]["name"] == "My Cool App"
    assert repos[0]["path"] == str(root / "my-cool-app")


async def test_sync_is_idempotent(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["app-one", "app-two"])
    monkeypatch.setattr(settings, "projects_root", str(root))

    first = (await client.get("/api/v1/repos", headers=AUTH)).json()
    second = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert len(first) == len(second) == 2
    assert [r["id"] for r in first] == [r["id"] for r in second]


async def test_rows_outside_the_root_are_hidden_not_deleted(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["real-app"])
    monkeypatch.setattr(settings, "projects_root", str(root))

    # junk row from an old test run / removed project — path outside the root
    stray = (await client.post(
        "/api/v1/repos",
        json={"slug": "stray", "name": "T", "path": "/private/var/pytest-junk/x"},
        headers=AUTH,
    )).json()

    listed = (await client.get("/api/v1/repos", headers=AUTH)).json()
    assert [r["slug"] for r in listed] == ["real-app"]

    # hidden from the list, but still fetchable by id — run history must survive
    got = await client.get(f"/api/v1/repos/{stray['id']}", headers=AUTH)
    assert got.status_code == 200


async def test_existing_registration_keeps_its_custom_name(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["acp-sandbox"])
    monkeypatch.setattr(settings, "projects_root", str(root))
    await client.post(
        "/api/v1/repos",
        json={"slug": "acp-sandbox", "name": "ACP Sandbox", "path": str(root / "acp-sandbox")},
        headers=AUTH,
    )

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert len(repos) == 1
    assert repos[0]["name"] == "ACP Sandbox"  # not overwritten to "Acp Sandbox"


async def test_planeignore_hides_a_project(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["wanted", "ignored"])
    (root / "ignored" / ".planeignore").touch()
    monkeypatch.setattr(settings, "projects_root", str(root))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert [r["slug"] for r in repos] == ["wanted"]


async def test_planeignore_hides_an_already_registered_project(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["proj"])
    monkeypatch.setattr(settings, "projects_root", str(root))
    assert len((await client.get("/api/v1/repos", headers=AUTH)).json()) == 1

    (root / "proj" / ".planeignore").touch()

    assert (await client.get("/api/v1/repos", headers=AUTH)).json() == []


async def test_description_comes_from_readme_first_paragraph(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["described"])
    (root / "described" / "README.md").write_text(
        "# described\n\nA control plane for agent handoffs —\nowns state and approvals.\n\n"
        "## More\nirrelevant detail\n"
    )
    monkeypatch.setattr(settings, "projects_root", str(root))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert repos[0]["description"] == (
        "A control plane for agent handoffs — owns state and approvals."
    )


async def test_no_readme_prose_means_no_description(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["bare", "heading-only"])
    (root / "heading-only" / "README.md").write_text("# heading-only\n")
    monkeypatch.setattr(settings, "projects_root", str(root))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert [r["description"] for r in repos] == [None, None]


async def test_description_skips_code_fences(db, client, tmp_path, monkeypatch):
    root = _root_with(tmp_path, git=["fenced"])
    (root / "fenced" / "README.md").write_text(
        "# fenced\n\n```sh\nnpm create astro@latest\n```\n\nA static site for wiring diagrams.\n"
    )
    monkeypatch.setattr(settings, "projects_root", str(root))

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert repos[0]["description"] == "A static site for wiring diagrams."


async def test_default_folder_name_gets_prettified_on_sync(db, client, tmp_path, monkeypatch):
    """Rows the old register flow created with name == folder name were never
    customised — sync upgrades those to the pretty name."""
    root = _root_with(tmp_path, git=["transcriber"])
    monkeypatch.setattr(settings, "projects_root", str(root))
    await client.post(
        "/api/v1/repos",
        json={"slug": "transcriber", "name": "transcriber", "path": str(root / "transcriber")},
        headers=AUTH,
    )

    repos = (await client.get("/api/v1/repos", headers=AUTH)).json()

    assert repos[0]["name"] == "Transcriber"
