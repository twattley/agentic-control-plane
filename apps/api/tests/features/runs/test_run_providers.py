"""Per-run agent choice: builder/reviewer provider specs ("provider[:model]")
stored on the run, resolved at dispatch, and expanded into CLI flags."""

from app.config import settings
from app.services import executor
from app.worker import _agent_command, _agent_message
from tests.conftest import AUTH


async def _repo_id(client) -> int:
    resp = await client.post(
        "/api/v1/repos",
        json={"slug": "tmp", "name": "tmp", "path": "/tmp/x"},
        headers=AUTH,
    )
    return resp.json()["id"]


# --- persistence -----------------------------------------------------------


async def test_run_persists_provider_choice(db, client):
    repo_id = await _repo_id(client)
    created = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo",
              "builder_provider": "claude:sonnet", "reviewer_provider": "codex"},
        headers=AUTH,
    )).json()

    assert created["builder_provider"] == "claude:sonnet"
    assert created["reviewer_provider"] == "codex"

    fetched = (await client.get(f"/api/v1/runs/{created['id']}", headers=AUTH)).json()
    assert fetched["run"]["builder_provider"] == "claude:sonnet"
    assert fetched["run"]["reviewer_provider"] == "codex"


async def test_provider_choice_defaults_to_null(db, client):
    repo_id = await _repo_id(client)
    created = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo"},
        headers=AUTH,
    )).json()
    assert created["builder_provider"] is None
    assert created["reviewer_provider"] is None


# --- dispatch resolution ---------------------------------------------------


async def test_dispatch_uses_the_runs_builder_provider(db, client, monkeypatch):
    calls = []
    monkeypatch.setattr(executor, "dispatch", lambda rid, role, provider=None:
                        calls.append((role, provider)))
    monkeypatch.setattr(settings, "dispatch_enabled", True)

    repo_id = await _repo_id(client)
    await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo",
              "builder_provider": "claude:sonnet"},
        headers=AUTH,
    )
    assert calls == [("builder", "claude:sonnet")]


async def test_dispatch_falls_back_to_global_provider(db, client, monkeypatch):
    calls = []
    monkeypatch.setattr(executor, "dispatch", lambda rid, role, provider=None:
                        calls.append((role, provider)))
    monkeypatch.setattr(settings, "dispatch_enabled", True)

    repo_id = await _repo_id(client)
    await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo"},
        headers=AUTH,
    )
    # None -> executor.dispatch resolves the global setting itself
    assert calls == [("builder", None)]


async def test_brief_dispatches_reviewer_with_runs_reviewer_provider(db, client, monkeypatch):
    calls = []
    monkeypatch.setattr(executor, "dispatch", lambda rid, role, provider=None:
                        calls.append((role, provider)))
    monkeypatch.setattr(settings, "dispatch_enabled", True)

    repo_id = await _repo_id(client)
    run_id = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo",
              "reviewer_provider": "codex"},
        headers=AUTH,
    )).json()["id"]
    calls.clear()

    await client.post(f"/api/v1/runs/{run_id}/claim",
                      json={"role": "builder", "holder": "x"}, headers=AUTH)
    await client.post(f"/api/v1/runs/{run_id}/events",
                      json={"type": "builder_brief_posted", "actor": "builder"}, headers=AUTH)

    assert calls == [("reviewer", "codex")]


async def test_manual_dispatch_accepts_provider_override(db, client, monkeypatch):
    calls = []
    monkeypatch.setattr(executor, "dispatch", lambda rid, role, provider=None:
                        calls.append((role, provider)))

    repo_id = await _repo_id(client)
    run_id = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo",
              "builder_provider": "claude:sonnet"},
        headers=AUTH,
    )).json()["id"]

    # explicit one-off override beats the run's stored choice
    resp = await client.post(f"/api/v1/runs/{run_id}/dispatch",
                             json={"provider": "codex"}, headers=AUTH)
    assert resp.status_code == 202
    assert calls == [("builder", "codex")]

    # bodyless dispatch (what a finishing worker sends) uses the run's choice
    calls.clear()
    resp = await client.post(f"/api/v1/runs/{run_id}/dispatch", headers=AUTH)
    assert resp.status_code == 202
    assert calls == [("builder", "claude:sonnet")]


# --- provider spec -> CLI command ------------------------------------------


def test_claude_spec_with_model_adds_model_flag():
    cmd = _agent_command("builder", "claude:sonnet", "do it", "/repo")
    assert cmd[:2] == ["claude", "-p"]
    assert ["--model", "sonnet"] == cmd[cmd.index("--model"):cmd.index("--model") + 2]
    assert "--permission-mode" in cmd


def test_claude_spec_without_model_has_no_model_flag():
    cmd = _agent_command("reviewer", "claude", "review it", "/repo")
    assert "--model" not in cmd
    assert "--permission-mode" not in cmd  # reviewer is read-only


def test_codex_spec_with_model_adds_model_flag():
    cmd = _agent_command("builder", "codex:gpt-5-codex", "do it", "/repo")
    assert cmd[:2] == ["codex", "exec"]
    assert ["-m", "gpt-5-codex"] == cmd[cmd.index("-m"):cmd.index("-m") + 2]


def test_claude_permission_mode_is_configurable(monkeypatch):
    monkeypatch.setattr(settings, "claude_permission_mode", "bypassPermissions")
    cmd = _agent_command("builder", "claude:sonnet", "do it", "/repo")
    assert ["--permission-mode", "bypassPermissions"] == \
        cmd[cmd.index("--permission-mode"):cmd.index("--permission-mode") + 2]


def test_agent_message_unwraps_claude_json_for_model_spec():
    stdout = '{"result": "all good"}'
    assert _agent_message(stdout, "claude:sonnet") == "all good"
