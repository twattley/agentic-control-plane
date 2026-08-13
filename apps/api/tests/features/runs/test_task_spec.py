from types import SimpleNamespace

from app.worker import _task_for


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
