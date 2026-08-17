"""Authoring stories from the UI: the plane never writes story files itself —
it shells out to the repo's own `agent_workflow create-story` (identity
allocation, epic membership), then merges the shaped body and handles the
backlog -> ready promotion."""

import json

from tests.conftest import AUTH

SKELETON = """# Do a thing

## Identity

- `kind`: `story`
- `story_id`: `E001-S00`
- `epic_id`: `E001`
- `coordination_class`: `feature`

## Status

- State: backlog
- Phase: shape
- Started: —
- Updated: 2026-08-15
- Completed: —
- Last: portable writer created E001-S00
- Next: shape scenarios and scope for E001-S00

## Story

Describe the user or operator outcome.

## Scenarios

### Scenario: Define observable behaviour

Given the relevant starting state
When the capability is used
Then define the observable outcome.

## Done When

- [ ] Define the observable story outcome.
"""

STANDALONE_SKELETON = SKELETON.replace(
    "- `story_id`: `E001-S00`\n- `epic_id`: `E001`",
    "- `story_id`: `S001`\n- `epic_id`: `none`",
)

CREATED_JSON = json.dumps({
    "story": {
        "coordination_class": "feature", "epic_id": "E001", "kind": "story",
        "path": "tickets/backlog/E001-S00-do-a-thing.md", "state": "backlog",
        "story_id": "E001-S00", "title": "Do a thing",
    },
    "updated_epic": "tickets/epics/E001-test-epic.md",
})

#: The real tool allocates `S###` and returns a null epic for --standalone.
STANDALONE_CREATED_JSON = json.dumps({
    "story": {
        "coordination_class": "feature", "epic_id": None, "kind": "story",
        "path": "tickets/backlog/S001-do-a-thing.md", "state": "backlog",
        "story_id": "S001", "title": "Do a thing",
    },
})

SHAPED_TICKET = (
    "# Do a thing\n\n## Summary\n\nA shaped outcome.\n\n"
    "## Capability\n\nShaped outcome.\n\n"
    "## Scope\n\n- `allowed_paths`:\n  - `app/**`\n\n"
    "## Validation\n\n```bash\nmake test\n```\n\n"
    "## Done When\n\n- [ ] The shaped outcome is observable.\n"
)


def _install_tool(repo, create_exit: int = 0) -> None:
    """A fake agent_workflow speaking the real create-story contract, including
    its exactly-one-parent-mode rule: an epic ID positional XOR --standalone.
    Every invocation appends its argv to args.log so tests can assert the
    parent mode actually sent to the tool."""
    scripts = repo / "scripts"
    scripts.mkdir(exist_ok=True)
    snapshot = json.dumps({
        "schema_version": "agent-workflow-snapshot-v1",
        "ticket_contract": "epic-story-v1",
        "epics": [], "runs": [], "diagnostics": [],
        "legacy": [{
            "kind": "legacy", "legacy_id": "old-cleanup",
            "title": "Clean up the parser", "path": "tickets/old-cleanup.md",
            "state": None,
        }],
        "stories": [{
            "kind": "story", "story_id": "E001-S00", "epic_id": "E001",
            "coordination_class": "feature", "state": "backlog",
            "title": "Do a thing", "path": "tickets/backlog/E001-S00-do-a-thing.md",
            "claimable_roles": [], "diagnostic_codes": [],
        }],
    })
    (repo / "skeleton.md").write_text(SKELETON)
    (repo / "skeleton_standalone.md").write_text(STANDALONE_SKELETON)
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> args.log\n'
        f"if [ \"$1\" = snapshot ]; then printf '%s\\n' '{snapshot}'; exit 0; fi\n"
        "if [ \"$1\" = create-story ]; then\n"
        f"  if [ {create_exit} -ne 0 ]; then echo boom >&2; exit {create_exit}; fi\n"
        "  mkdir -p tickets/backlog\n"
        "  case \"$*\" in\n"
        "    *--standalone*)\n"
        "      cp skeleton_standalone.md tickets/backlog/S001-do-a-thing.md\n"
        f"      printf '%s\\n' '{STANDALONE_CREATED_JSON}' ;;\n"
        "    *)\n"
        "      cp skeleton.md tickets/backlog/E001-S00-do-a-thing.md\n"
        f"      printf '%s\\n' '{CREATED_JSON}' ;;\n"
        "  esac\n"
        "  exit 0\n"
        "fi\n"
        "exit 92\n"
    )
    command.chmod(0o755)


def _create_story_argv(repo) -> str:
    """The argv of the single create-story invocation."""
    calls = [
        line for line in (repo / "args.log").read_text().splitlines()
        if line.startswith("create-story")
    ]
    assert len(calls) == 1, calls
    return calls[0]


async def _repo(client, tmp_path) -> int:
    (tmp_path / "tickets").mkdir(exist_ok=True)
    resp = await client.post(
        "/api/v1/repos", json={"slug": "p", "name": "P", "path": str(tmp_path)}, headers=AUTH
    )
    return resp.json()["id"]


async def test_create_story_delegates_to_the_repo_tool(db, client, tmp_path):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"epic_id": "E001", "coordination_class": "feature", "title": "Do a thing"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["story_id"] == "E001-S00"
    assert body["state"] == "backlog"
    created = tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md"
    assert "## Identity" in created.read_text()
    # The tool takes exactly one parent mode; an epic must not also send the flag.
    argv = _create_story_argv(tmp_path)
    assert "E001" in argv
    assert "--standalone" not in argv


async def test_create_standalone_story_sends_the_standalone_flag(db, client, tmp_path):
    """A repo with no epics must still be able to author first-class work.
    Omitting epic_id means standalone — not legacy, and not a failure."""
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"epic_id": None, "coordination_class": "feature", "title": "Do a thing"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["story_id"] == "S001"
    assert body["epic_id"] is None
    assert body["state"] == "backlog"
    # Exactly one parent mode: the flag, and no epic positional.
    argv = _create_story_argv(tmp_path)
    assert "--standalone" in argv
    assert "None" not in argv
    assert "## Identity" in (
        tmp_path / "tickets" / "backlog" / "S001-do-a-thing.md"
    ).read_text()


async def test_create_standalone_story_merges_shaped_body(db, client, tmp_path):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"coordination_class": "feature", "title": "Do a thing",
              "body": "## Story\n\nStandalone outcome.\n"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    text = (tmp_path / "tickets" / "backlog" / "S001-do-a-thing.md").read_text()
    assert "Standalone outcome." in text
    assert "Describe the user or operator outcome." not in text


async def test_create_story_merges_shaped_body_below_status(db, client, tmp_path):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    body_md = "## Story\n\nCSV export of runs for the analyst.\n\n## Done When\n\n- [ ] works\n"
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"epic_id": "E001", "coordination_class": "feature",
              "title": "Do a thing", "body": body_md},
        headers=AUTH,
    )

    assert resp.status_code == 201
    text = (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").read_text()
    assert "## Identity" in text and "- State: backlog" in text  # tool header kept
    assert "CSV export of runs for the analyst." in text          # shaped body in
    assert "Describe the user or operator outcome." not in text   # skeleton body out


async def test_create_story_without_tool_conflicts(db, client, tmp_path):
    repo_id = await _repo(client, tmp_path)
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"epic_id": "E001", "coordination_class": "feature", "title": "x"},
        headers=AUTH,
    )
    assert resp.status_code == 409


async def test_create_story_tool_failure_is_502(db, client, tmp_path):
    _install_tool(tmp_path, create_exit=1)
    repo_id = await _repo(client, tmp_path)
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"epic_id": "E001", "coordination_class": "feature", "title": "x"},
        headers=AUTH,
    )
    assert resp.status_code == 502


async def test_mark_ready_moves_file_and_updates_status(db, client, tmp_path):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)
    await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"epic_id": "E001", "coordination_class": "feature", "title": "Do a thing"},
        headers=AUTH,
    )

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/E001-S00/ready", headers=AUTH
    )

    assert resp.status_code == 200
    assert resp.json()["state"] == "ready"
    moved = tmp_path / "tickets" / "ready" / "E001-S00-do-a-thing.md"
    assert moved.is_file()
    assert not (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").exists()
    text = moved.read_text()
    assert "- State: ready" in text
    assert "- Phase: queued" in text
    assert "- `story_id`: `E001-S00`" in text  # identity untouched


async def test_mark_ready_unknown_story_404(db, client, tmp_path):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/E009-S99/ready", headers=AUTH
    )
    assert resp.status_code == 404


async def test_adopt_legacy_ticket_as_story(db, client, tmp_path):
    """The contract's explicit migration: a human picks the epic, the tool
    allocates identity, the legacy content becomes the story body, and the
    legacy file goes away."""
    _install_tool(tmp_path)
    legacy = tmp_path / "tickets" / "old-cleanup.md"
    legacy.parent.mkdir(exist_ok=True)
    legacy.write_text("# Clean up the parser\n\nDrop the dead branches in the parser.\n")
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/adopt",
        json={"legacy_id": "old-cleanup", "epic_id": "E001", "coordination_class": "feature"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    assert resp.json()["story_id"] == "E001-S00"
    story_text = (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").read_text()
    assert "Drop the dead branches in the parser." in story_text
    assert "## Identity" in story_text
    assert not legacy.exists()


async def test_adopt_legacy_ticket_as_a_standalone_story(db, client, tmp_path):
    """Adoption is how live legacy work leaves the Legacy bucket. A repo with
    no epics must be able to adopt without inventing one."""
    _install_tool(tmp_path)
    legacy = tmp_path / "tickets" / "old-cleanup.md"
    legacy.parent.mkdir(exist_ok=True)
    legacy.write_text("# Clean up the parser\n\nDrop the dead branches in the parser.\n")
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/adopt",
        json={"legacy_id": "old-cleanup", "epic_id": None, "coordination_class": "feature"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    assert resp.json()["story_id"] == "S001"
    assert resp.json()["epic_id"] is None
    assert "--standalone" in _create_story_argv(tmp_path)
    story_text = (tmp_path / "tickets" / "backlog" / "S001-do-a-thing.md").read_text()
    assert "Drop the dead branches in the parser." in story_text
    assert not legacy.exists()


async def test_adopt_unknown_legacy_404_and_tool_failure_keeps_the_file(db, client, tmp_path):
    _install_tool(tmp_path, create_exit=1)
    legacy = tmp_path / "tickets" / "old-cleanup.md"
    legacy.parent.mkdir(exist_ok=True)
    legacy.write_text("# Keep me\n")
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/adopt",
        json={"legacy_id": "nope", "epic_id": "E001", "coordination_class": "feature"},
        headers=AUTH,
    )
    assert resp.status_code == 404

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/adopt",
        json={"legacy_id": "old-cleanup", "epic_id": "E001", "coordination_class": "feature"},
        headers=AUTH,
    )
    assert resp.status_code == 502
    assert legacy.exists()  # nothing lost on failure


async def test_freeze_into_a_story(db, client, tmp_path, monkeypatch):
    """A contract-repo freeze creates a story via the tool, not a flat ticket."""
    from app.services import discussion_agent

    async def fake_reply(repo_path, message, session_id):
        if message == discussion_agent.FREEZE_PROMPT:
            return "sess-1", SHAPED_TICKET
        return "sess-1", "echo"

    monkeypatch.setattr(discussion_agent, "reply", fake_reply)
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions", json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"epic_id": "E001", "coordination_class": "feature"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    assert resp.json()["slug"] == "E001-S00"
    text = (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").read_text()
    assert "Shaped outcome." in text
    assert "## Identity" in text
    disc = (await client.get(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}", headers=AUTH
    )).json()["discussion"]
    assert disc["state"] == "frozen"
    assert disc["ticket_slug"] == "E001-S00"


async def _frozen_discussion(client, repo_id, monkeypatch) -> int:
    from app.services import discussion_agent

    async def fake_reply(repo_path, message, session_id):
        if message == discussion_agent.FREEZE_PROMPT:
            return "sess-1", SHAPED_TICKET
        return "sess-1", "echo"

    monkeypatch.setattr(discussion_agent, "reply", fake_reply)
    return (await client.post(
        f"/api/v1/repos/{repo_id}/discussions", json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]


async def test_freeze_into_a_standalone_story(db, client, tmp_path, monkeypatch):
    """Shaping an idea in a contract repo with no epics must still produce a
    story. Before standalone existed this fell through to a flat legacy file."""
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)
    disc_id = await _frozen_discussion(client, repo_id, monkeypatch)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"standalone": True, "coordination_class": "feature"},
        headers=AUTH,
    )

    assert resp.status_code == 200
    assert resp.json()["slug"] == "S001"
    assert "--standalone" in _create_story_argv(tmp_path)
    text = (tmp_path / "tickets" / "backlog" / "S001-do-a-thing.md").read_text()
    assert "Shaped outcome." in text
    assert "## Identity" in text
    # The flat-ticket fallback must not have fired.
    assert not (tmp_path / "tickets" / "do-a-thing.md").exists()


async def test_freeze_without_a_parent_mode_is_422(db, client, tmp_path, monkeypatch):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)
    disc_id = await _frozen_discussion(client, repo_id, monkeypatch)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"coordination_class": "feature"}, headers=AUTH,
    )

    assert resp.status_code == 422
