"""A Control Plane builder claim owns the ready -> in-progress lane move."""

import subprocess

from app import worker
from app.worker import run_pass
from tests.conftest import AUTH
from tests.features.runs.test_dispatch import _git_repo, _state

STORY_ID = "S002"
STORY_NAME = "S002-do-a-thing.md"


def _install_story_workflow(repo_dir) -> None:
    ready = repo_dir / "tickets" / "ready"
    ready.mkdir(parents=True)
    (ready / STORY_NAME).write_text(
        """# Do a thing

## Identity

- `kind`: `story`
- `story_id`: `S002`
- `epic_id`: `none`
- `coordination_class`: `platform`

## Status

- State: ready
- Phase: queued
- Started: —
- Updated: —
- Completed: —
- Last: —
- Next: builder
"""
    )

    scripts = repo_dir / "scripts"
    scripts.mkdir()
    adapter = scripts / "agent_workflow"
    adapter.write_text(
        f"""#!/usr/bin/env python3
import json
from pathlib import Path

story_name = "{STORY_NAME}"
in_progress = Path("tickets/in-progress") / story_name
state = "in-progress" if in_progress.is_file() else "ready"
payload = {{
    "schema_version": "agent-workflow-snapshot-v2",
    "ticket_contract": "epic-story-v1",
    "epics": [],
    "stories": [{{
        "kind": "story",
        "story_id": "{STORY_ID}",
        "epic_id": None,
        "coordination_class": "platform",
        "state": state,
        "title": "Do a thing",
        "path": f"tickets/{{state}}/{{story_name}}",
        "claimable_roles": (
            ["builder", "reviewer"] if state == "in-progress" else ["builder"]
        ),
        "diagnostic_codes": [],
    }}],
    "legacy": [],
    "runs": [],
    "diagnostics": [],
}}
print(json.dumps(payload))
"""
    )
    adapter.chmod(0o755)

    closer = scripts / "close_ticket"
    closer.write_text(
        f"""#!/bin/sh
if [ ! -f tickets/in-progress/{STORY_NAME} ]; then
  echo 'Ticket must be in tickets/in-progress' >&2
  exit 1
fi
"""
    )
    closer.chmod(0o755)


async def test_builder_claim_moves_ready_story_before_the_pass_and_first_close_succeeds(
    db, client, tmp_path, monkeypatch
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_story_workflow(repo_dir)
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)
    subprocess.run(
        [
            "git", "-C", str(repo_dir),
            "-c", "user.email=t@t", "-c", "user.name=t",
            "commit", "-q", "-m", "story",
        ],
        check=True,
    )
    repo_id = (
        await client.post(
            "/api/v1/repos",
            json={
                "slug": "lane-move",
                "name": "Lane move",
                "path": str(repo_dir),
                "close_gate_command": "true",
            },
            headers=AUTH,
        )
    ).json()["id"]
    run_id = (
        await client.post(
            "/api/v1/runs",
            json={"repo_id": repo_id, "ticket_id": STORY_ID, "title": "Do a thing"},
            headers=AUTH,
        )
    ).json()["id"]

    async def observe_claimed_pass(_pool, _run_id, _role, _provider, _detail, _repo, task):
        assert await _state(client, run_id) == "building"
        assert not (repo_dir / "tickets" / "ready" / STORY_NAME).exists()
        assert (repo_dir / "tickets" / "in-progress" / STORY_NAME).is_file()
        assert f"tickets/in-progress/{STORY_NAME}" in task
        return "done"

    monkeypatch.setattr(worker, "_run_claimed_pass", observe_claimed_pass)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    async def post(path, body):
        return await client.post(
            f"/api/v1/runs/{run_id}{path}", json=body, headers=AUTH
        )

    await post("/events", {"type": "builder_brief_posted", "actor": "builder"})
    await post("/claim", {"role": "reviewer", "holder": "claude"})
    await post(
        "/events",
        {
            "type": "reviewer_findings_posted",
            "actor": "reviewer",
            "payload": {"verdict": "pass"},
        },
    )
    await post("/decision", {"decision": "approve"})
    await post("/decision", {"decision": "close"})

    assert await run_pass(db, run_id, "closer", "system") == "done"
    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    assert detail["run"]["state"] == "closed"
    assert not any(event["type"] == "gate_failed" for event in detail["events"])
