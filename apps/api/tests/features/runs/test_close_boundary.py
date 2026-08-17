"""The closer enforces the ticket boundary against repository state."""

import json
import subprocess
from pathlib import Path

from app.worker import run_pass
from tests.features.runs.test_dispatch import (
    _drive_to_closing,
    _gate_event,
    _git_repo,
    _run_on,
    _state,
)

STORY_ID = "S001"
STORY_NAME = "S001-scoped-change.md"
PROJECT_ROOT = Path(__file__).resolve().parents[5]


def _install_scoped_story(repo_dir) -> None:
    ticket = repo_dir / "tickets" / "in-progress" / STORY_NAME
    ticket.parent.mkdir(parents=True)
    ticket.write_text(
        f"""# Scoped change

## Identity

- `kind`: `story`
- `story_id`: `{STORY_ID}`
- `epic_id`: `none`
- `coordination_class`: `platform`

## Scope

- `allowed_paths`:
  - allowed.py
- `read_context_paths`:
  - README.md
- `forbidden_paths`:
  - secrets/**
"""
    )

    payload = {
        "schema_version": "agent-workflow-snapshot-v2",
        "ticket_contract": "epic-story-v1",
        "epics": [],
        "stories": [
            {
                "kind": "story",
                "story_id": STORY_ID,
                "epic_id": None,
                "coordination_class": "platform",
                "state": "in-progress",
                "title": "Scoped change",
                "path": f"tickets/in-progress/{STORY_NAME}",
                "claimable_roles": ["builder", "reviewer"],
                "diagnostic_codes": [],
            }
        ],
        "legacy": [],
        "runs": [],
        "diagnostics": [],
    }
    scripts = repo_dir / "scripts"
    scripts.mkdir()
    adapter = scripts / "agent_workflow"
    adapter.write_text(
        "#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(payload)}'\n"
    )
    adapter.chmod(0o755)
    (scripts / "check_ticket_scope").symlink_to(
        PROJECT_ROOT / "scripts" / "check_ticket_scope"
    )

    (repo_dir / "allowed.py").write_text("VALUE = 1\n")
    secrets = repo_dir / "secrets"
    secrets.mkdir()
    (secrets / "session.txt").write_text("sid=BASELINE\n")
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "scope fixture",
        ],
        check=True,
    )


def _head(repo_dir) -> str:
    return subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def _install_moving_closer(repo_dir) -> None:
    closer = repo_dir / "scripts" / "close_ticket"
    closer.write_text(
        "#!/usr/bin/env python3\n"
        "from pathlib import Path\n"
        f"name = {STORY_NAME!r}\n"
        "source = Path('tickets/in-progress') / name\n"
        "destination = Path('tickets/done') / name\n"
        "destination.parent.mkdir(parents=True, exist_ok=True)\n"
        "source.replace(destination)\n"
        "adapter = Path('scripts/agent_workflow')\n"
        "adapter.write_text(adapter.read_text().replace(\n"
        "    'tickets/in-progress/', 'tickets/done/'\n"
        "))\n"
    )
    closer.chmod(0o755)


def _committed_paths(repo_dir) -> list[str]:
    return subprocess.run(
        ["git", "-C", str(repo_dir), "show", "--format=", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()


async def test_forbidden_staged_path_refuses_close_and_commits_nothing(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir, ticket=STORY_ID, gate="true")
    _install_scoped_story(repo_dir)
    await _drive_to_closing(client, run_id)
    head_before = _head(repo_dir)
    (repo_dir / "allowed.py").write_text("VALUE = 2\n")
    (repo_dir / "secrets" / "session.txt").write_text("sid=TEST_SECRET\n")
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    assert _head(repo_dir) == head_before
    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_failed"
    assert "secrets/session.txt" in event["payload"]["summary"]
    staged = subprocess.run(
        ["git", "-C", str(repo_dir), "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert "secrets/session.txt" not in staged


async def test_incidental_path_is_left_uncommitted_while_allowed_work_closes(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir, ticket=STORY_ID, gate="true")
    _install_scoped_story(repo_dir)
    await _drive_to_closing(client, run_id)
    (repo_dir / "allowed.py").write_text("VALUE = 2\n")
    (repo_dir / "notes.txt").write_text("unrelated human note\n")
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "closed"
    assert _committed_paths(repo_dir) == ["allowed.py"]
    status = subprocess.run(
        ["git", "-C", str(repo_dir), "status", "--short"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert status == ["A  notes.txt"]


async def test_scoped_commit_includes_the_ticket_move_but_not_incidental_work(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir, ticket=STORY_ID, gate="true")
    _install_scoped_story(repo_dir)
    _install_moving_closer(repo_dir)
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "closer fixture",
        ],
        check=True,
    )
    await _drive_to_closing(client, run_id)
    (repo_dir / "allowed.py").write_text("VALUE = 2\n")
    (repo_dir / "notes.txt").write_text("unrelated human note\n")
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "closed"
    done_story = f"tickets/done/{STORY_NAME}"
    assert set(_committed_paths(repo_dir)) == {"allowed.py", done_story}
    assert subprocess.run(
        ["git", "-C", str(repo_dir), "cat-file", "-e", f"HEAD:{done_story}"],
        check=False,
    ).returncode == 0
    assert subprocess.run(
        ["git", "-C", str(repo_dir), "cat-file", "-e", "HEAD:notes.txt"],
        capture_output=True,
        check=False,
    ).returncode != 0
    assert set(subprocess.run(
        ["git", "-C", str(repo_dir), "status", "--short"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()) == {"A  notes.txt", " M scripts/agent_workflow"}


async def test_scoped_commit_carries_an_uncommitted_prior_ticket_lane(
    db, client, tmp_path
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir, ticket=STORY_ID, gate="true")
    _install_scoped_story(repo_dir)
    in_progress = repo_dir / "tickets" / "in-progress" / STORY_NAME
    ready = repo_dir / "tickets" / "ready" / STORY_NAME
    ready.parent.mkdir()
    in_progress.replace(ready)
    adapter = repo_dir / "scripts" / "agent_workflow"
    adapter.write_text(
        adapter.read_text()
        .replace('"state": "in-progress"', '"state": "ready"')
        .replace("tickets/in-progress/", "tickets/ready/")
    )
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-q",
            "-m",
            "ready fixture",
        ],
        check=True,
    )
    ready.replace(in_progress)
    adapter.write_text(
        adapter.read_text()
        .replace('"state": "ready"', '"state": "in-progress"')
        .replace("tickets/ready/", "tickets/in-progress/")
    )
    await _drive_to_closing(client, run_id)
    (repo_dir / "allowed.py").write_text("VALUE = 2\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "closed"
    assert subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "cat-file",
            "-e",
            f"HEAD:tickets/in-progress/{STORY_NAME}",
        ],
        capture_output=True,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        [
            "git",
            "-C",
            str(repo_dir),
            "cat-file",
            "-e",
            f"HEAD:tickets/ready/{STORY_NAME}",
        ],
        capture_output=True,
        check=False,
    ).returncode != 0
