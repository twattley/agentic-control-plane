import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.features.workflow import repository as workflow_repository
from tests.conftest import AUTH


async def _register(client, path: str) -> int:
    response = await client.post(
        "/api/v1/repos",
        json={"slug": "portable", "name": "Portable", "path": path},
        headers=AUTH,
    )
    return response.json()["id"]


def _install_snapshot(repo, payload: dict, exit_code: int = 0) -> None:
    scripts = repo / "scripts"
    scripts.mkdir()
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n"
        "test \"$#\" -eq 1 || exit 91\n"
        "test \"$1\" = snapshot || exit 92\n"
        f"printf '%s\\n' '{json.dumps(payload)}'\n"
        f"exit {exit_code}\n"
    )
    command.chmod(0o755)


def _install_raw(repo, stdout: str, exit_code: int = 0, delay: int = 0) -> None:
    scripts = repo / "scripts"
    scripts.mkdir()
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n"
        "test \"$1\" = snapshot || exit 92\n"
        + (f"sleep {delay}\n" if delay else "")
        + f"printf '%s\\n' '{stdout}'\n"
        + f"exit {exit_code}\n"
    )
    command.chmod(0o755)


def _snapshot(**overrides) -> dict:
    payload = {
        "schema_version": "agent-workflow-snapshot-v1",
        "ticket_contract": "epic-story-v1",
        "epics": [],
        "stories": [],
        "legacy": [],
        "runs": [],
        "diagnostics": [],
    }
    payload.update(overrides)
    return payload


def _story(story_id: str = "E001-S00", **overrides) -> dict:
    story = {
        "kind": "story",
        "story_id": story_id,
        "epic_id": "E001",
        "coordination_class": "feature",
        "state": "ready",
        "title": "Render status",
        "path": f"tickets/ready/{story_id}-render-status.md",
        "claimable_roles": ["builder"],
        "diagnostic_codes": [],
    }
    story.update(overrides)
    return story


def _legacy(legacy_id: str = "OLD-1", **overrides) -> dict:
    item = {
        "kind": "legacy",
        "legacy_id": legacy_id,
        "title": "Old ticket",
        "path": f"tickets/{legacy_id}.md",
        "state": None,
    }
    item.update(overrides)
    return item


def _portable_run(work_unit_id: str, ticket_kind: str | None, **overrides) -> dict:
    run = {
        "id": "abc123",
        "project_slug": "portable",
        "work_unit_id": work_unit_id,
        "ticket_path": f"tickets/ready/{work_unit_id}.md",
        "agent": "codex",
        "role": "builder",
        "status": "claimed",
        "independent_review": None,
        "git_ref": "main@abc",
        "claimed_at": "2026-08-15T00:00:00+00:00",
        "completed_at": None,
        "abandoned_at": None,
        "last_event": "claimed",
        "last_event_at": "2026-08-15T00:00:00+00:00",
        "ticket_kind": ticket_kind,
    }
    run.update(overrides)
    return run


def _tree(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob("*") if path.is_file()
    }


async def test_exact_snapshot_is_preserved_by_authenticated_workflow_route(client, tmp_path):
    snapshot = _snapshot(
        epics=[{
            "kind": "epic",
            "epic_id": "E001",
            "title": "Deliver portable status",
            "path": "tickets/epics/E001-deliver-portable-status.md",
            "story_ids": ["E001-S00"],
            "story_counts": {
                "backlog": 0, "ready": 1, "in-progress": 0,
                "blocked": 0, "complete": 0, "total": 1,
            },
        }],
        stories=[{
            "kind": "story",
            "story_id": "E001-S00",
            "epic_id": "E001",
            "coordination_class": "feature",
            "state": "ready",
            "title": "Render status",
            "path": "tickets/ready/E001-S00-render-status.md",
            "claimable_roles": ["builder"],
            "diagnostic_codes": [],
        }],
    )
    _install_snapshot(tmp_path, snapshot)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {"source": "agent-workflow-snapshot-v1", **snapshot}


async def test_v2_snapshot_without_standalone_stories_reads_unchanged(client, tmp_path):
    """The version bump alone must not break an existing reader. This is the
    case that lets agentic-engineering flip its emitter without blanking every
    project page in every repo that has the portable tool installed."""
    snapshot = _snapshot(
        schema_version="agent-workflow-snapshot-v2", stories=[_story()],
    )
    _install_snapshot(tmp_path, snapshot)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {"source": "agent-workflow-snapshot-v2", **snapshot}


async def test_v2_standalone_story_has_no_parent_epic(client, tmp_path):
    """A standalone story is a first-class story with no epic. `epic_id` is
    null, and that must survive the read rather than be invented into a
    parent."""
    snapshot = _snapshot(
        schema_version="agent-workflow-snapshot-v2",
        stories=[_story(story_id="S001", epic_id=None,
                        path="tickets/ready/S001-quick-fix.md")],
    )
    _install_snapshot(tmp_path, snapshot)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 200
    story = response.json()["stories"][0]
    assert story["story_id"] == "S001"
    assert story["epic_id"] is None


async def test_v1_still_rejects_a_null_parent_epic(client, tmp_path):
    """Tolerating v2 must not quietly relax v1. A v1 snapshot claiming a
    null-parented story is malformed, not standalone."""
    _install_snapshot(
        tmp_path, _snapshot(stories=[_story(story_id="S001", epic_id=None)]),
    )
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 502


async def test_nonzero_diagnostic_snapshot_remains_usable(client, tmp_path):
    diagnostic = {
        "source": "ticket",
        "code": "state_mismatch",
        "message": "declared ready, located in backlog",
        "path": "tickets/backlog/E001-S00-render-status.md",
        "related_paths": [],
    }
    _install_snapshot(tmp_path, _snapshot(diagnostics=[diagnostic]), exit_code=1)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 200
    assert response.json()["diagnostics"] == [diagnostic]


def test_adapter_uses_fixed_argv_cwd_timeout_and_no_shell(tmp_path, monkeypatch):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    command = scripts / "agent_workflow"
    command.write_text("#!/bin/sh\n")
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured.update(kwargs)
        return SimpleNamespace(stdout=json.dumps(_snapshot()), returncode=0)

    monkeypatch.setattr(workflow_repository.subprocess, "run", fake_run)

    workflow_repository.load_workflow(str(tmp_path))

    assert captured["argv"] == [str(command), "snapshot"]
    assert captured["cwd"] == tmp_path.resolve()
    assert captured["timeout"] == workflow_repository._TIMEOUT_SECONDS
    assert captured.get("shell", False) is False


@pytest.mark.parametrize(
    "stdout",
    [
        "not json",
        # v3 is the unknown one now: tolerating v2 must not mean tolerating
        # whatever comes next.
        json.dumps(_snapshot(schema_version="agent-workflow-snapshot-v3")),
        json.dumps({"schema_version": "agent-workflow-snapshot-v1"}),
        json.dumps(_snapshot(epics=[{
            "kind": "epic",
            "epic_id": "E001",
            "title": "Wrongly typed progress",
            "path": "tickets/epics/E001-wrongly-typed-progress.md",
            "story_ids": [],
            "story_counts": {
                "backlog": 0, "ready": "1", "in-progress": 0,
                "blocked": 0, "complete": 0, "total": 1,
            },
        }])),
    ],
)
async def test_present_invalid_adapter_is_an_explicit_error_without_fallback(
    client, tmp_path, stdout
):
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "LEGACY.md").write_text("# Must not become fallback")
    _install_raw(tmp_path, stdout)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 502
    assert "legacy-flat" not in response.text


async def test_undecodable_snapshot_output_is_an_explicit_error_without_fallback(
    client, tmp_path
):
    """A snapshot that is not valid UTF-8 is a broken adapter, not an absent one.

    `text=True` decodes strictly, and UnicodeDecodeError is a ValueError — so it
    slipped past the OSError handler and escaped as an unhandled 500 rather than
    the 502 every other adapter failure returns.
    """
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "LEGACY.md").write_text("# Must not become fallback")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n"
        'test "$1" = snapshot || exit 92\n'
        "printf '\\376\\377bad bytes'\n"  # a UTF-16 BOM: never valid UTF-8
    )
    command.chmod(0o755)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 502
    assert "legacy-flat" not in response.text


async def test_snapshot_timeout_is_an_explicit_error(client, tmp_path, monkeypatch):
    _install_raw(tmp_path, json.dumps(_snapshot()), delay=1)
    monkeypatch.setattr(workflow_repository, "_TIMEOUT_SECONDS", 0.01)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 502
    assert "failed" in response.json()["detail"]


async def test_missing_adapter_uses_top_level_legacy_only_and_is_read_only(client, tmp_path):
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "OLD-1.md").write_text("# Old one\n\nKeep this.")
    nested = tickets / "ready"
    nested.mkdir()
    (nested / "NESTED.md").write_text("# Must not be discovered")
    before = _tree(tmp_path)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "legacy-flat"
    assert body["schema_version"] is None
    assert [item["legacy_id"] for item in body["legacy"]] == ["OLD-1"]
    assert _tree(tmp_path) == before


async def test_epics_story_counts_and_empty_epics_are_preserved(client, tmp_path):
    epics = [
        {
            "kind": "epic",
            "epic_id": "E001",
            "title": "Full epic",
            "path": "tickets/epics/E001-full.md",
            "story_ids": ["E001-S00"],
            "story_counts": {
                "backlog": 0, "ready": 1, "in-progress": 0,
                "blocked": 0, "complete": 0, "total": 1,
            },
        },
        {
            "kind": "epic",
            "epic_id": "E002",
            "title": "Empty epic",
            "path": "tickets/epics/E002-empty.md",
            "story_ids": [],
            "story_counts": {
                "backlog": 0, "ready": 0, "in-progress": 0,
                "blocked": 0, "complete": 0, "total": 0,
            },
        },
    ]
    _install_snapshot(tmp_path, _snapshot(epics=epics, stories=[_story()]))
    repo_id = await _register(client, str(tmp_path))

    body = (await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)).json()

    assert body["epics"] == epics


async def test_portable_and_orphan_runs_remain_distinct_and_visible(client, tmp_path):
    runs = [
        _portable_run("E001-S00", "story"),
        _portable_run("MISSING", None, id="orphan"),
    ]
    diagnostic = {
        "source": "ledger",
        "code": "orphan_run",
        "message": "no ticket matches MISSING",
        "path": ".agent-workflow/runs/orphan.json",
        "related_paths": [],
    }
    _install_snapshot(
        tmp_path,
        _snapshot(stories=[_story()], runs=runs, diagnostics=[diagnostic]),
        exit_code=1,
    )
    repo_id = await _register(client, str(tmp_path))

    body = (await client.get(f"/api/v1/repos/{repo_id}/workflow", headers=AUTH)).json()

    assert [(run["work_unit_id"], run["ticket_kind"]) for run in body["runs"]] == [
        ("E001-S00", "story"),
        ("MISSING", None),
    ]
    assert body["diagnostics"] == [diagnostic]


async def test_document_resolves_stable_identity_to_current_locator(client, tmp_path):
    path = tmp_path / "tickets" / "in-progress" / "E001-S00-clearer-name.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Current title\n\nCurrent summary.\n")
    story = _story(
        path="tickets/in-progress/E001-S00-clearer-name.md",
        state="in-progress",
        title="Current title",
    )
    _install_snapshot(tmp_path, _snapshot(stories=[story]))
    before = _tree(tmp_path)
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(
        f"/api/v1/repos/{repo_id}/workflow/documents/E001-S00", headers=AUTH
    )

    assert response.status_code == 200
    assert response.json() == {
        "identity": "E001-S00",
        "kind": "story",
        "path": "tickets/in-progress/E001-S00-clearer-name.md",
        "title": "Current title",
        "summary": "Current summary.",
        "content": "# Current title\n\nCurrent summary.\n",
    }
    assert _tree(tmp_path) == before


@pytest.mark.parametrize(
    "locator",
    ["/tmp/outside.md", "tickets/../outside.md", "tickets/ready/missing.md"],
)
async def test_document_rejects_absolute_escaping_or_missing_locator(
    client, tmp_path, locator
):
    (tmp_path / "outside.md").write_text("# secret")
    _install_snapshot(tmp_path, _snapshot(stories=[_story(path=locator)]))
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(
        f"/api/v1/repos/{repo_id}/workflow/documents/E001-S00", headers=AUTH
    )

    assert response.status_code == 404
    assert "secret" not in response.text


async def test_document_rejects_duplicate_identity(client, tmp_path):
    _install_snapshot(
        tmp_path,
        _snapshot(stories=[_story(), _story(path="tickets/ready/duplicate.md")]),
    )
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(
        f"/api/v1/repos/{repo_id}/workflow/documents/E001-S00", headers=AUTH
    )

    assert response.status_code == 404
    assert "not unique" in response.json()["detail"]


async def test_ready_story_starts_exact_identity_once(client, tmp_path):
    ticket = tmp_path / "tickets" / "ready" / "E001-S00-render-status.md"
    ticket.parent.mkdir(parents=True)
    ticket.write_text("# Render status\n")
    _install_snapshot(tmp_path, _snapshot(stories=[_story()]))
    repo_id = await _register(client, str(tmp_path))
    request = {
        "repo_id": repo_id,
        "ticket_id": "E001-S00",
        "title": "Render status",
    }

    response = await client.post("/api/v1/runs", json=request, headers=AUTH)
    duplicate = await client.post("/api/v1/runs", json=request, headers=AUTH)

    assert response.status_code == 201
    assert response.json()["ticket_id"] == "E001-S00"
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "stories",
    [
        [_story(path="tickets/ready/missing.md")],
        [_story(path="tickets/../outside.md")],
        [_story(), _story(path="tickets/ready/duplicate.md")],
    ],
    ids=["missing", "escaping", "duplicate"],
)
async def test_story_with_unresolvable_document_cannot_start(client, tmp_path, stories):
    outside = tmp_path / "outside.md"
    outside.write_text("# Must not be read\n")
    _install_snapshot(tmp_path, _snapshot(stories=stories))
    repo_id = await _register(client, str(tmp_path))

    response = await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "E001-S00", "title": "No"},
        headers=AUTH,
    )

    assert response.status_code == 409


@pytest.mark.parametrize(
    "story",
    [
        _story(state="backlog", claimable_roles=[]),
        _story(state="in-progress", claimable_roles=["reviewer"]),
        _story(state="blocked", claimable_roles=[]),
        _story(state="complete", claimable_roles=[]),
        _story(diagnostic_codes=["state_mismatch"], claimable_roles=[]),
    ],
    ids=["backlog", "in-progress", "blocked", "complete", "diagnosed"],
)
async def test_non_startable_story_is_rejected(client, tmp_path, story):
    _install_snapshot(tmp_path, _snapshot(stories=[story]))
    repo_id = await _register(client, str(tmp_path))

    response = await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "E001-S00", "title": "No"},
        headers=AUTH,
    )

    assert response.status_code == 409


async def test_opted_in_legacy_cannot_start_new_run(client, tmp_path):
    _install_snapshot(tmp_path, _snapshot(legacy=[_legacy()]))
    repo_id = await _register(client, str(tmp_path))

    response = await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "OLD-1", "title": "Old"},
        headers=AUTH,
    )

    assert response.status_code == 409


async def test_migrating_legacy_keeps_existing_start_behavior(client, tmp_path):
    _install_snapshot(
        tmp_path,
        _snapshot(ticket_contract=None, legacy=[_legacy()]),
    )
    repo_id = await _register(client, str(tmp_path))

    response = await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "OLD-1", "title": "Old"},
        headers=AUTH,
    )

    assert response.status_code == 201


async def test_workflow_requires_authentication(client, tmp_path):
    repo_id = await _register(client, str(tmp_path))

    response = await client.get(f"/api/v1/repos/{repo_id}/workflow")

    assert response.status_code == 401
