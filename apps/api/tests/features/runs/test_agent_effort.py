"""Per-role reasoning effort: a service-wide operator setting per role, expanded
into the provider-appropriate CLI flag and propagated to detached workers.

Effort rides the settings seam (not the `provider[:model]` spec), mirroring how
`claude_permission_mode` already reaches `_agent_command`.
"""

import subprocess

from app.config import Settings, settings
from app.services import executor
from app.worker import _agent_command


def _adjacent(cmd: list[str], flag: str) -> list[str]:
    """The flag and the token right after it — for asserting `["--effort", "high"]`."""
    i = cmd.index(flag)
    return cmd[i:i + 2]


def test_dogfood_role_defaults_are_sonnet_medium_and_opus_high(monkeypatch):
    for name in (
        "AGENTIC_CONTROL_PLANE_BUILDER_PROVIDER",
        "AGENTIC_CONTROL_PLANE_REVIEWER_PROVIDER",
        "AGENTIC_CONTROL_PLANE_BUILDER_EFFORT",
        "AGENTIC_CONTROL_PLANE_REVIEWER_EFFORT",
    ):
        monkeypatch.delenv(name, raising=False)

    defaults = Settings(database_url="postgresql://unused", _env_file=None)

    assert (
        defaults.builder_provider,
        defaults.builder_effort,
        defaults.reviewer_provider,
        defaults.reviewer_effort,
    ) == ("claude:sonnet", "medium", "claude:opus", "high")


# --- claude: a first-class --effort flag -----------------------------------


def test_claude_builder_includes_effort_when_set(monkeypatch):
    # Done When #1 requires the full argv pinned, not just the --effort pair, so
    # a stray, duplicated, or misplaced argument fails the check too.
    monkeypatch.setattr(settings, "builder_effort", "high")
    cmd = _agent_command("builder", "claude:fable-5", "do it", "/repo")
    assert cmd == [
        "claude", "-p", "do it", "--output-format", "json",
        "--model", "fable-5",
        "--permission-mode", settings.claude_permission_mode,
        "--effort", "high",
    ]


def test_reviewer_effort_drives_reviewer_independently(monkeypatch):
    monkeypatch.setattr(settings, "builder_effort", "low")
    monkeypatch.setattr(settings, "reviewer_effort", "high")

    builder = _agent_command("builder", "claude:fable-5", "do it", "/repo")
    reviewer = _agent_command("reviewer", "claude", "review it", "/repo")

    assert _adjacent(builder, "--effort") == ["--effort", "low"]
    assert _adjacent(reviewer, "--effort") == ["--effort", "high"]


# --- codex: a -c config override -------------------------------------------


def test_codex_builder_includes_effort_override_when_set(monkeypatch):
    monkeypatch.setattr(settings, "builder_effort", "high")
    cmd = _agent_command("builder", "codex", "do it", "/repo")
    assert _adjacent(cmd, "-c") == ["-c", "model_reasoning_effort=high"]


# --- unset reproduces today's behavior exactly -----------------------------


def test_effort_unset_leaves_claude_argv_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "builder_effort", "")
    cmd = _agent_command("builder", "claude:fable-5", "do it", "/repo")
    assert cmd == [
        "claude", "-p", "do it", "--output-format", "json",
        "--model", "fable-5",
        "--permission-mode", settings.claude_permission_mode,
    ]


def test_effort_unset_leaves_codex_argv_unchanged(monkeypatch):
    monkeypatch.setattr(settings, "builder_effort", "")
    cmd = _agent_command("builder", "codex", "do it", "/repo")
    assert cmd == ["codex", "exec", "do it", "-s", "workspace-write", "-C", "/repo"]


def test_effort_on_stub_is_a_no_op(monkeypatch):
    monkeypatch.setattr(settings, "builder_effort", "high")
    cmd = _agent_command("builder", "stub", "do it", "/repo")
    assert "--effort" not in cmd
    assert not any("model_reasoning_effort" in part for part in cmd)
    assert cmd[0] == "bash"  # the stub's own command, unperturbed


# --- detached workers receive the configured efforts -----------------------


def test_dispatch_child_env_carries_both_efforts(monkeypatch):
    monkeypatch.setattr(settings, "builder_effort", "high")
    monkeypatch.setattr(settings, "reviewer_effort", "medium")

    captured = {}
    monkeypatch.setattr(subprocess, "Popen",
                        lambda *a, **kw: captured.update(kw) or None)

    executor.dispatch(1, "builder", "stub")

    env = captured["env"]
    assert env["AGENTIC_CONTROL_PLANE_BUILDER_EFFORT"] == "high"
    assert env["AGENTIC_CONTROL_PLANE_REVIEWER_EFFORT"] == "medium"
