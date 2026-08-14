"""Ticket-shaping discussions: bounce with a repo-grounded agent, then freeze
into a ticket file. The agent is faked — no test ever spawns a real CLI."""

import pytest

from app.services import discussion_agent
from tests.conftest import AUTH

TICKET_MD = "# Add exports\n\n## Summary\n\nCSV export of runs.\n\n## Done means\n\n- [ ] works\n"


@pytest.fixture
def agent_calls(monkeypatch):
    """Fake the CLI turn: echo replies, return the ticket markdown on freeze."""
    calls = []

    async def fake_reply(repo_path, message, session_id):
        calls.append({"repo_path": repo_path, "message": message, "session_id": session_id})
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
    assert agent_calls[0]["repo_path"] == str(tmp_path)  # agent ran in the checkout


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
