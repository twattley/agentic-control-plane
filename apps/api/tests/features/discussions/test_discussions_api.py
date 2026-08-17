"""Ticket-shaping discussions: bounce with a repo-grounded agent, then freeze
into a ticket file. The agent is faked — no test ever spawns a real CLI."""

import pytest

from app.services import discussion_agent
from tests.conftest import AUTH

TICKET_MD = (
    "# Add exports\n\n## Summary\n\nCSV export of runs.\n\n"
    "## Capability\n\nAn owner can export runs as CSV.\n\n"
    "## Scope\n\n- `allowed_paths`:\n  - `app/**`\n\n"
    "## Validation\n\n```bash\nmake test\n```\n\n"
    "## Done When\n\n- [ ] Exported runs are valid CSV.\n"
)


@pytest.fixture
def agent_calls(monkeypatch):
    """Fake the CLI turn: echo replies, return the ticket markdown on freeze."""
    calls = []

    async def fake_reply(repo_path, message, session_id, skill_prompt=None):
        calls.append({
            "repo_path": repo_path,
            "message": message,
            "session_id": session_id,
            "skill_prompt": skill_prompt,
        })
        if message == discussion_agent.FREEZE_PROMPT:
            return "sess-1", f"```markdown\n{TICKET_MD}```"
        return "sess-1", f"echo: {message}"

    monkeypatch.setattr(discussion_agent, "reply", fake_reply)
    return calls


async def _repo(client, tmp_path) -> int:
    resp = await client.post(
        "/api/v1/repos", json={"slug": "t", "name": "T", "path": str(tmp_path)}, headers=AUTH
    )
    return resp.json()["id"]


def _skill(root, name: str, description: str, instruction: str = "Ask sharp questions."):
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: >\n  {description}\n---\n\n{instruction}\n"
    )
    return skill_file


async def test_skills_are_discovered_live_with_repo_override(
    db, client, tmp_path, monkeypatch
):
    user_skills = tmp_path / "user-skills"
    repo_dir = tmp_path / "repo"
    _skill(user_skills, "grill", "user description")
    _skill(repo_dir / ".claude" / "skills", "grill", "repo description")
    monkeypatch.setattr(discussion_agent, "USER_SKILLS_DIR", user_skills)
    repo_id = await _repo(client, repo_dir)

    first = await client.get(
        f"/api/v1/repos/{repo_id}/discussions/skills", headers=AUTH
    )
    _skill(user_skills, "shape-feature", "shape a feature")
    second = await client.get(
        f"/api/v1/repos/{repo_id}/discussions/skills", headers=AUTH
    )

    assert first.json() == [{"name": "grill", "description": "repo description"}]
    assert second.json() == [
        {"name": "grill", "description": "repo description"},
        {"name": "shape-feature", "description": "shape a feature"},
    ]


async def test_start_records_both_sides_and_the_session(db, client, tmp_path, agent_calls):
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "I want CSV export"}, headers=AUTH,
    )

    assert resp.status_code == 201
    detail = resp.json()
    assert [m["role"] for m in detail["messages"]] == ["human", "agent"]
    assert detail["messages"][1]["content"] == "echo: I want CSV export"
    assert detail["discussion"]["session_id"] == "sess-1"
    assert detail["discussion"]["skill_name"] is None
    assert agent_calls[0]["repo_path"] == str(tmp_path)  # agent ran in the checkout
    assert agent_calls[0]["skill_prompt"] is None


async def test_start_with_skill_frames_and_records_the_discussion(
    db, client, tmp_path, agent_calls
):
    repo_dir = tmp_path / "repo"
    skill_file = _skill(
        repo_dir / ".claude" / "skills",
        "grill-to-tests",
        "turn an idea into tests",
        "Ask one contract question at a time.",
    )
    repo_id = await _repo(client, repo_dir)

    response = await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "shape exports", "skill_name": "grill-to-tests"},
        headers=AUTH,
    )

    assert response.status_code == 201
    assert response.json()["discussion"]["skill_name"] == "grill-to-tests"
    assert agent_calls[0]["skill_prompt"] == skill_file.read_text()


async def test_unavailable_skill_fails_before_discussion_is_created(
    db, client, tmp_path, agent_calls
):
    repo_id = await _repo(client, tmp_path)

    response = await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "shape exports", "skill_name": "missing"},
        headers=AUTH,
    )
    discussions = await client.get(
        f"/api/v1/repos/{repo_id}/discussions", headers=AUTH
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "skill 'missing' is not available"
    assert discussions.json() == []


async def test_freeze_notes_the_skill_and_keeps_it_readable(
    db, client, tmp_path, agent_calls
):
    repo_dir = tmp_path / "repo"
    _skill(
        repo_dir / ".claude" / "skills",
        "grill-to-tests",
        "turn an idea into tests",
    )
    repo_id = await _repo(client, repo_dir)
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "shape exports", "skill_name": "grill-to-tests"},
        headers=AUTH,
    )).json()["discussion"]["id"]

    response = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"slug": "T-7"}, headers=AUTH,
    )
    discussion = (await client.get(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}", headers=AUTH
    )).json()["discussion"]
    ticket = (repo_dir / "tickets" / "T-7.md").read_text()

    assert response.status_code == 200
    assert discussion["skill_name"] == "grill-to-tests"
    assert "Shaped with `grill-to-tests`" in ticket


def test_skill_note_is_added_after_the_ticket_title():
    noted = discussion_agent.note_skill(TICKET_MD, "grill-to-tests")

    assert noted.startswith(
        "# Add exports\n\n> Shaped with `grill-to-tests`.\n\n## Summary"
    )


async def test_next_message_resumes_the_session(db, client, tmp_path, agent_calls):
    repo_id = await _repo(client, tmp_path)
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/messages",
        json={"message": "narrower scope"}, headers=AUTH,
    )

    assert resp.status_code == 200
    assert len(resp.json()["messages"]) == 4
    assert agent_calls[-1]["session_id"] == "sess-1"  # resumed, not restarted


async def test_freeze_writes_the_ticket_via_the_plane(db, client, tmp_path, agent_calls):
    repo_id = await _repo(client, tmp_path)
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"slug": "T-7"}, headers=AUTH,
    )

    assert resp.status_code == 200
    assert resp.json()["title"] == "Add exports"
    assert resp.json()["summary"] == "CSV export of runs."
    assert (tmp_path / "tickets" / "T-7.md").read_text() == TICKET_MD  # fence stripped

    disc = (await client.get(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}", headers=AUTH
    )).json()["discussion"]
    assert disc["state"] == "frozen"
    assert disc["ticket_slug"] == "T-7"


async def test_freeze_conflict_on_existing_ticket_stays_open(db, client, tmp_path, agent_calls):
    repo_id = await _repo(client, tmp_path)
    (tmp_path / "tickets").mkdir()
    (tmp_path / "tickets" / "T-7.md").write_text("# already\n")
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"slug": "T-7"}, headers=AUTH,
    )

    assert resp.status_code == 409
    disc = (await client.get(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}", headers=AUTH
    )).json()["discussion"]
    assert disc["state"] == "open"  # pick another slug and freeze again


async def test_freeze_without_allowed_paths_writes_nothing_and_stays_open(
    db, client, tmp_path, monkeypatch
):
    async def fake_reply(repo_path, message, session_id):
        if message == discussion_agent.FREEZE_PROMPT:
            return "sess-1", (
                "# Add exports\n\n## Summary\n\nCSV export of runs.\n\n"
                "## Scope\n\n- `allowed_paths`:\n\n"
                "## Validation\n\n```bash\nmake test\n```\n"
            )
        return "sess-1", f"echo: {message}"

    monkeypatch.setattr(discussion_agent, "reply", fake_reply)
    repo_id = await _repo(client, tmp_path)
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"slug": "T-7"}, headers=AUTH,
    )

    assert resp.status_code == 422
    assert "allowed_paths" in resp.json()["detail"]
    assert not (tmp_path / "tickets" / "T-7.md").exists()
    continued = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/messages",
        json={"message": "scope it to the exporter"}, headers=AUTH,
    )
    assert continued.status_code == 200


async def test_freeze_with_empty_validation_writes_nothing_and_stays_open(
    db, client, tmp_path, monkeypatch
):
    async def fake_reply(repo_path, message, session_id):
        if message == discussion_agent.FREEZE_PROMPT:
            return "sess-1", (
                "# Add exports\n\n## Summary\n\nCSV export of runs.\n\n"
                "## Scope\n\n- `allowed_paths`:\n  - `app/**`\n\n## Validation\n"
            )
        return "sess-1", f"echo: {message}"

    monkeypatch.setattr(discussion_agent, "reply", fake_reply)
    repo_id = await _repo(client, tmp_path)
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
        json={"slug": "T-7"}, headers=AUTH,
    )

    assert resp.status_code == 422
    assert "Validation" in resp.json()["detail"]
    assert not (tmp_path / "tickets" / "T-7.md").exists()
    continued = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/messages",
        json={"message": "use make test"}, headers=AUTH,
    )
    assert continued.status_code == 200


async def test_frozen_discussion_refuses_more_messages(db, client, tmp_path, agent_calls):
    repo_id = await _repo(client, tmp_path)
    disc_id = (await client.post(
        f"/api/v1/repos/{repo_id}/discussions",
        json={"message": "hi"}, headers=AUTH,
    )).json()["discussion"]["id"]
    await client.post(f"/api/v1/repos/{repo_id}/discussions/{disc_id}/freeze",
                      json={"slug": "T-7"}, headers=AUTH)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions/{disc_id}/messages",
        json={"message": "one more thing"}, headers=AUTH,
    )

    assert resp.status_code == 409


async def test_agent_failure_records_nothing(db, client, tmp_path, monkeypatch):
    async def broken(repo_path, message, session_id):
        raise discussion_agent.AgentError("boom")

    monkeypatch.setattr(discussion_agent, "reply", broken)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/discussions", json={"message": "hi"}, headers=AUTH
    )

    assert resp.status_code == 502
    discs = (await client.get(f"/api/v1/repos/{repo_id}/discussions", headers=AUTH)).json()
    assert discs[0]["session_id"] is None  # row exists but no messages recorded
    detail = (await client.get(
        f"/api/v1/repos/{repo_id}/discussions/{discs[0]['id']}", headers=AUTH
    )).json()
    assert detail["messages"] == []


async def test_discussions_require_token(db, client, tmp_path):
    repo_id = await _repo(client, tmp_path)
    resp = await client.post(f"/api/v1/repos/{repo_id}/discussions", json={"message": "hi"})
    assert resp.status_code == 401


def test_shaping_prompts_pin_sizing_depth_and_ticket_contract():
    system = discussion_agent._SYSTEM
    assert "Size the request first" in system
    assert "one question at a time" in system
    assert "recommended answer" in system
    assert "Given/When/Then" in system
    assert "should not happen" in system

    for section_name in ("Summary", "Capability", "Scope", "Validation", "Done When"):
        assert f"## {section_name}" in discussion_agent.FREEZE_PROMPT
    assert "allowed_paths" in discussion_agent.FREEZE_PROMPT
    assert "forbidden_paths" in discussion_agent.FREEZE_PROMPT


@pytest.mark.parametrize("skill_prompt", [None, "Ask one contract question."])
async def test_shaping_agent_subprocess_remains_read_only(
    monkeypatch, tmp_path, skill_prompt
):
    calls = []

    class FakeProcess:
        returncode = 0

        async def communicate(self):
            return b'{"session_id":"sess-2","result":"ready"}', b""

    async def fake_subprocess(*cmd, **kwargs):
        calls.append((cmd, kwargs))
        return FakeProcess()

    monkeypatch.setattr(discussion_agent.asyncio, "create_subprocess_exec", fake_subprocess)

    result = await discussion_agent.reply(
        str(tmp_path), "shape this", None, skill_prompt
    )

    assert result == ("sess-2", "ready")
    cmd, kwargs = calls[0]
    assert "--permission-mode" not in cmd
    system_prompt = cmd[cmd.index("--append-system-prompt") + 1]
    assert system_prompt.startswith(discussion_agent._SYSTEM)
    assert ("Ask one contract question." in system_prompt) == bool(skill_prompt)
    assert kwargs["cwd"] == str(tmp_path)
