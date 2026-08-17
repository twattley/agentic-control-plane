"""A dispatched role runs the kit's method (acp-034).

The role's method comes from the installed skill layer (ROLE.md, authored in
agentic-engineering, ae-022); the plane composes it with its own run context
and output contract. Plane tests pin the seam, the kit's tests pin the words.
"""

import pytest

from app import worker
from app.worker import _task_for, _with_role_method, run_pass
from tests.conftest import AUTH
from tests.features.runs.conftest import STUB_BUILDER_METHOD, STUB_REVIEWER_METHOD
from tests.features.runs.test_dispatch import _git_repo, _run_on
from tests.features.runs.test_task_spec import _detail


def test_builder_prompt_is_method_then_run_context(tmp_path):
    task = _with_role_method("builder", _task_for(_detail(), "builder", str(tmp_path)))

    assert task.startswith(STUB_BUILDER_METHOD)
    assert "Implement SBX-3: Do the thing." in task
    assert "SUMMARY: <one sentence>" in task  # harness contract stays plane-owned
    assert STUB_REVIEWER_METHOD not in task


def test_reviewer_prompt_is_method_then_run_context(tmp_path):
    task = _with_role_method("reviewer", _task_for(_detail(), "reviewer", str(tmp_path)))

    assert task.startswith(STUB_REVIEWER_METHOD)
    assert "VERDICT: pass" in task  # the parser's contract, composed by the plane
    assert STUB_BUILDER_METHOD not in task


def test_missing_role_method_raises_naming_the_file(role_methods):
    (role_methods / "builder" / "ROLE.md").unlink()

    with pytest.raises(worker.RoleMethodMissingError, match="builder/ROLE.md"):
        _with_role_method("builder", "Implement t1.")


def test_empty_role_method_is_missing_not_silent(role_methods):
    (role_methods / "reviewer" / "ROLE.md").write_text("   \n")

    with pytest.raises(worker.RoleMethodMissingError, match="reviewer/ROLE.md"):
        _with_role_method("reviewer", "Review t1.")


async def test_missing_method_fails_the_pass_like_a_crash(
    db, client, tmp_path, role_methods
):
    """No silent fallback: the pass dies loudly, the event names the file,
    and the run lands where a crashed pass lands (awaiting_human)."""
    (role_methods / "builder" / "ROLE.md").unlink()
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    with pytest.raises(worker.RoleMethodMissingError):
        await run_pass(db, run_id, "builder", "stub")

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    failure = detail["events"][-1]
    assert failure["type"] == "worker_failed"
    assert "builder/ROLE.md" in failure["payload"]["error"]
    assert detail["run"]["state"] == "awaiting_human"
