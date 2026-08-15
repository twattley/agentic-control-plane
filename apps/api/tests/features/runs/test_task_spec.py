import json
from types import SimpleNamespace

import pytest

from app.features.workflow import repository as workflow_repository
from app.services import runs_service
from app.worker import _task_for, run_pass
from tests.conftest import AUTH


def _detail(ticket_id="SBX-3", mode="direct", events=(), artifacts=()):
    run = SimpleNamespace(ticket_id=ticket_id, title="Do the thing", mode=mode)
    return SimpleNamespace(run=run, events=list(events), artifacts=list(artifacts))


def test_builder_task_points_at_ticket_file_when_present(tmp_path):
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "SBX-3.md").write_text("# spec")

    task = _task_for(_detail(), "builder", str(tmp_path))

    assert "tickets/SBX-3.md" in task


def test_builder_task_unchanged_without_ticket_file(tmp_path):
    task = _task_for(_detail(), "builder", str(tmp_path))
    assert task == "Implement SBX-3: Do the thing."


def test_reviewer_task_points_at_ticket_file_when_present(tmp_path):
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "SBX-3.md").write_text("# spec")

    task = _task_for(_detail(), "reviewer", str(tmp_path))

    assert "tickets/SBX-3.md" in task
    assert "VERDICT" in task


def test_fix_pass_keeps_spec_pointer(tmp_path):
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "SBX-3.md").write_text("# spec")
    findings = SimpleNamespace(
        type="reviewer_findings_posted", payload={"summary": "fix the loop"}
    )

    task = _task_for(_detail(events=[findings]), "builder", str(tmp_path))

    assert "fix the loop" in task
    assert "tickets/SBX-3.md" in task


def test_prompt_follows_stable_identity_to_current_snapshot_locator(tmp_path):
    current = tmp_path / "tickets" / "in-progress" / "E001-S00-current.md"
    current.parent.mkdir(parents=True)
    current.write_text("# Current")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    payload = {
        "schema_version": "agent-workflow-snapshot-v1",
        "ticket_contract": "epic-story-v1",
        "epics": [],
        "stories": [{
            "kind": "story", "story_id": "E001-S00", "epic_id": "E001",
            "coordination_class": "feature", "state": "in-progress",
            "title": "Current", "path": "tickets/in-progress/E001-S00-current.md",
            "claimable_roles": ["reviewer"], "diagnostic_codes": [],
        }],
        "legacy": [], "runs": [], "diagnostics": [],
    }
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(payload)}'\n"
    )
    command.chmod(0o755)

    task = _task_for(_detail(ticket_id="E001-S00"), "builder", str(tmp_path))

    assert "tickets/in-progress/E001-S00-current.md" in task
    assert "tickets/E001-S00.md" not in task


def test_story_prompt_frames_the_small_goal_inside_the_epic(tmp_path):
    """The point of the hierarchy: the agent is told the broad outcome (epic)
    and the slice it must deliver now (story) — and only that slice."""
    story_file = tmp_path / "tickets" / "ready" / "E001-S02-build-bootstrap.md"
    story_file.parent.mkdir(parents=True)
    story_file.write_text("# Build bootstrap")
    epic_file = tmp_path / "tickets" / "epics" / "E001-capture-every-source.md"
    epic_file.parent.mkdir(parents=True)
    epic_file.write_text("# Capture every source")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    payload = {
        "schema_version": "agent-workflow-snapshot-v1",
        "ticket_contract": "epic-story-v1",
        "epics": [{
            "kind": "epic", "epic_id": "E001", "title": "Capture every source",
            "path": "tickets/epics/E001-capture-every-source.md",
            "story_ids": ["E001-S02"], "story_counts": {"total": 1},
        }],
        "stories": [{
            "kind": "story", "story_id": "E001-S02", "epic_id": "E001",
            "coordination_class": "feature", "state": "ready",
            "title": "Build bootstrap", "path": "tickets/ready/E001-S02-build-bootstrap.md",
            "claimable_roles": ["builder"], "diagnostic_codes": [],
        }],
        "legacy": [], "runs": [], "diagnostics": [],
    }
    command = scripts / "agent_workflow"
    command.write_text("#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(payload)}'\n")
    command.chmod(0o755)

    builder_task = _task_for(_detail(ticket_id="E001-S02"), "builder", str(tmp_path))
    reviewer_task = _task_for(_detail(ticket_id="E001-S02"), "reviewer", str(tmp_path))

    for task in (builder_task, reviewer_task):
        assert "tickets/ready/E001-S02-build-bootstrap.md" in task   # the small goal
        assert "E001: Capture every source" in task                   # the big goal
        assert "tickets/epics/E001-capture-every-source.md" in task   # where to read it
        assert "only this story" in task                              # and the boundary


@pytest.mark.parametrize(
    "stories",
    [
        [{
            "kind": "story", "story_id": "E001-S00", "epic_id": "E001",
            "coordination_class": "feature", "state": "ready",
            "title": "Missing", "path": "tickets/ready/missing.md",
            "claimable_roles": ["builder"], "diagnostic_codes": [],
        }],
        [
            {
                "kind": "story", "story_id": "E001-S00", "epic_id": "E001",
                "coordination_class": "feature", "state": "ready",
                "title": "Duplicate", "path": "tickets/ready/first.md",
                "claimable_roles": ["builder"], "diagnostic_codes": [],
            },
            {
                "kind": "story", "story_id": "E001-S00", "epic_id": "E001",
                "coordination_class": "feature", "state": "ready",
                "title": "Duplicate", "path": "tickets/ready/second.md",
                "claimable_roles": ["builder"], "diagnostic_codes": [],
            },
        ],
    ],
    ids=["missing", "duplicate"],
)
def test_prompt_surfaces_snapshot_document_resolution_failure(tmp_path, stories):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    payload = {
        "schema_version": "agent-workflow-snapshot-v1",
        "ticket_contract": "epic-story-v1",
        "epics": [], "stories": stories, "legacy": [], "runs": [],
        "diagnostics": [],
    }
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(payload)}'\n"
    )
    command.chmod(0o755)

    with pytest.raises(workflow_repository.WorkflowDocumentError):
        _task_for(_detail(ticket_id="E001-S00"), "builder", str(tmp_path))


async def test_prompt_resolution_failure_leaves_worker_run_unclaimed(
    db, client, tmp_path
):
    tickets = tmp_path / "tickets"
    tickets.mkdir()
    (tickets / "T-1.md").write_text("# Startable before adapter\n")
    repo_response = await client.post(
        "/api/v1/repos",
        json={"slug": "prompt-failure", "name": "Prompt failure", "path": str(tmp_path)},
        headers=AUTH,
    )
    run_response = await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_response.json()["id"], "ticket_id": "T-1", "title": "Test"},
        headers=AUTH,
    )
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    payload = {
        "schema_version": "agent-workflow-snapshot-v1",
        "ticket_contract": "epic-story-v1",
        "epics": [],
        "stories": [{
            "kind": "story", "story_id": "T-1", "epic_id": "E001",
            "coordination_class": "feature", "state": "ready",
            "title": "Now unsafe", "path": "tickets/ready/missing.md",
            "claimable_roles": ["builder"], "diagnostic_codes": [],
        }],
        "legacy": [], "runs": [], "diagnostics": [],
    }
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(payload)}'\n"
    )
    command.chmod(0o755)

    with pytest.raises(workflow_repository.WorkflowDocumentError):
        await run_pass(db, run_response.json()["id"], "builder", "stub")

    detail = await runs_service.run_detail(db, run_response.json()["id"])
    assert detail.run.state == "queued"
