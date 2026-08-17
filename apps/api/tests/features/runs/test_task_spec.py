import json
from types import SimpleNamespace

import pytest

from app.features.workflow import repository as workflow_repository
from app.services import runs_service
from app.worker import _task_for, run_pass
from tests.conftest import AUTH


def _detail(ticket_id="SBX-3", mode="direct", events=(), artifacts=(), run_id=7):
    run = SimpleNamespace(id=run_id, ticket_id=ticket_id, title="Do the thing", mode=mode)
    return SimpleNamespace(run=run, events=list(events), artifacts=list(artifacts))


def test_builder_task_points_at_ticket_file_when_present(tmp_path):
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "SBX-3.md").write_text("# spec")

    task = _task_for(_detail(), "builder", str(tmp_path))

    assert "tickets/SBX-3.md" in task


def test_builder_task_has_no_spec_pointer_without_a_ticket_file(tmp_path):
    task = _task_for(_detail(), "builder", str(tmp_path))
    assert task.startswith("Implement SBX-3: Do the thing.")
    assert "specification is in" not in task


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


def test_fix_pass_carries_the_human_note_when_it_is_the_newest_word(tmp_path):
    """A human who requests changes has, by definition, disagreed with a
    reviewer who just passed the work. Prompting from the findings alone tells
    the builder to fix nothing — the objection never reaches it."""
    findings = SimpleNamespace(
        type="reviewer_findings_posted", payload={"summary": "No blocking findings."}
    )
    note = SimpleNamespace(
        type="human_note_posted", payload={"note": "wrap it in an RTVIngestor"}
    )

    task = _task_for(_detail(events=[findings, note]), "builder", str(tmp_path))

    assert "wrap it in an RTVIngestor" in task
    assert "No blocking findings." not in task


def test_fix_pass_ignores_a_human_note_the_reviewer_has_already_answered(tmp_path):
    """Order is what makes the note current. A note from an earlier round was
    already addressed; the newest reviewer findings win."""
    note = SimpleNamespace(
        type="human_note_posted", payload={"note": "old objection"}
    )
    findings = SimpleNamespace(
        type="reviewer_findings_posted", payload={"summary": "fix the loop"}
    )

    task = _task_for(_detail(events=[note, findings]), "builder", str(tmp_path))

    assert "fix the loop" in task
    assert "old objection" not in task


def test_fix_pass_falls_back_to_findings_when_the_note_is_empty(tmp_path):
    """An empty note carries no instruction. Preferring it would replace real
    findings with nothing — worse than not having asked."""
    findings = SimpleNamespace(
        type="reviewer_findings_posted", payload={"summary": "fix the loop"}
    )
    blank = SimpleNamespace(type="human_note_posted", payload={"note": None})

    task = _task_for(_detail(events=[findings, blank]), "builder", str(tmp_path))

    assert "fix the loop" in task


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


def test_standalone_story_prompt_invents_no_epic(tmp_path):
    """A standalone story has no parent by design. The prompt must say nothing
    about an epic rather than reach for the nearest one."""
    story_file = tmp_path / "tickets" / "ready" / "S001-quick-fix.md"
    story_file.parent.mkdir(parents=True)
    story_file.write_text("# Quick fix")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    payload = {
        "schema_version": "agent-workflow-snapshot-v2",
        "ticket_contract": "epic-story-v1",
        "epics": [{
            "kind": "epic", "epic_id": "E001", "title": "Capture every source",
            "path": "tickets/epics/E001-capture-every-source.md",
            "story_ids": [], "story_counts": {"total": 0},
        }],
        "stories": [{
            "kind": "story", "story_id": "S001", "epic_id": None,
            "coordination_class": "feature", "state": "ready",
            "title": "Quick fix", "path": "tickets/ready/S001-quick-fix.md",
            "claimable_roles": ["builder"], "diagnostic_codes": [],
        }],
        "legacy": [], "runs": [], "diagnostics": [],
    }
    command = scripts / "agent_workflow"
    command.write_text("#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(payload)}'\n")
    command.chmod(0o755)

    task = _task_for(_detail(ticket_id="S001"), "builder", str(tmp_path))

    assert "tickets/ready/S001-quick-fix.md" in task  # the story is still found
    assert "E001" not in task                          # but no parent invented
    assert "one slice of epic" not in task


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


def _v1_story_repo(tmp_path, story_id="E001-S00"):
    """A snapshot-tool repo with one resolvable v1 story."""
    story_file = tmp_path / "tickets" / "ready" / f"{story_id}-do-a-thing.md"
    story_file.parent.mkdir(parents=True)
    story_file.write_text("# Do a thing")
    payload = {
        "schema_version": "agent-workflow-snapshot-v1",
        "ticket_contract": "epic-story-v1",
        "epics": [],
        "stories": [{
            "kind": "story", "story_id": story_id, "epic_id": "E001",
            "coordination_class": "feature", "state": "ready",
            "title": "Do a thing", "path": f"tickets/ready/{story_id}-do-a-thing.md",
            "claimable_roles": ["builder"], "diagnostic_codes": [],
        }],
        "legacy": [], "runs": [], "diagnostics": [],
    }
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    command = scripts / "agent_workflow"
    command.write_text("#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(payload)}'\n")
    command.chmod(0o755)


def test_builder_task_for_a_v1_story_carries_the_status_contract(tmp_path):
    """S001's builder wrote 'Phase: review-ready' and dropped Started and
    Completed — three of the four hand repairs its close needed. The prompt is
    where the plane states the portable contract the file must keep satisfying."""
    _v1_story_repo(tmp_path)

    task = _task_for(_detail(ticket_id="E001-S00"), "builder", str(tmp_path))

    assert "Phase: review-loop" in task
    for field in ("State", "Phase", "Started", "Updated", "Completed", "Last", "Next"):
        assert field in task
    assert "exactly one" in task  # never a second ## Status block


def test_fix_pass_for_a_v1_story_keeps_the_status_contract(tmp_path):
    _v1_story_repo(tmp_path)
    findings = SimpleNamespace(
        type="reviewer_findings_posted", payload={"summary": "fix the loop"}
    )

    task = _task_for(_detail(ticket_id="E001-S00", events=[findings]), "builder", str(tmp_path))

    assert "fix the loop" in task
    assert "Phase: review-loop" in task


def test_reviewer_task_carries_no_status_contract(tmp_path):
    """The reviewer is read-only; instructing it to edit status invites edits."""
    _v1_story_repo(tmp_path)

    task = _task_for(_detail(ticket_id="E001-S00"), "reviewer", str(tmp_path))

    assert "Phase: review-loop" not in task


def test_legacy_flat_builder_task_carries_no_status_contract(tmp_path):
    """Legacy tickets close at Phase: review, not review-loop — instructing the
    v1 vocabulary there would recreate the mismatch in the other direction."""
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "SBX-3.md").write_text("# spec")

    task = _task_for(_detail(), "builder", str(tmp_path))

    assert "review-loop" not in task
