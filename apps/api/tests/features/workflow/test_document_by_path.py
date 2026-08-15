"""Reading a work document by its path. Identity is for runs; a path is for
display — nested legacy files that share a filename stem must still be
readable, which an identity lookup cannot do."""

import json

from tests.conftest import AUTH

SNAPSHOT = {
    "schema_version": "agent-workflow-snapshot-v1",
    "ticket_contract": "epic-story-v1",
    "epics": [], "stories": [], "runs": [], "diagnostics": [],
    "legacy": [
        {"kind": "legacy", "legacy_id": "00-overview", "title": "Overview A",
         "path": "tickets/backlog/alpha/00-overview.md", "state": "backlog"},
        {"kind": "legacy", "legacy_id": "00-overview", "title": "Overview B",
         "path": "tickets/backlog/beta/00-overview.md", "state": "backlog"},
    ],
}


def _install(repo) -> None:
    for folder, body in [("alpha", "# Overview A\n\nAlpha body.\n"),
                         ("beta", "# Overview B\n\nBeta body.\n")]:
        target = repo / "tickets" / "backlog" / folder
        target.mkdir(parents=True)
        (target / "00-overview.md").write_text(body)
    scripts = repo / "scripts"
    scripts.mkdir()
    command = scripts / "agent_workflow"
    command.write_text("#!/bin/sh\n" + f"printf '%s\\n' '{json.dumps(SNAPSHOT)}'\n")
    command.chmod(0o755)


async def _repo(client, tmp_path) -> int:
    resp = await client.post(
        "/api/v1/repos", json={"slug": "p", "name": "P", "path": str(tmp_path)}, headers=AUTH
    )
    return resp.json()["id"]


async def test_colliding_stems_are_each_readable_by_path(db, client, tmp_path):
    _install(tmp_path)
    repo_id = await _repo(client, tmp_path)

    for folder, expected in [("alpha", "Alpha body."), ("beta", "Beta body.")]:
        resp = await client.get(
            f"/api/v1/repos/{repo_id}/workflow/document",
            params={"path": f"tickets/backlog/{folder}/00-overview.md"}, headers=AUTH,
        )
        assert resp.status_code == 200, resp.text
        assert expected in resp.json()["content"]

    # the identity route still refuses the ambiguous stem — runs need one file
    ambiguous = await client.get(
        f"/api/v1/repos/{repo_id}/workflow/documents/00-overview", headers=AUTH
    )
    assert ambiguous.status_code == 404


async def test_document_by_path_rejects_escapes(db, client, tmp_path):
    _install(tmp_path)
    (tmp_path / "secret.md").write_text("# secret\n")
    repo_id = await _repo(client, tmp_path)

    for bad in ["../secret.md", "/etc/hosts", "tickets/../secret.md", "tickets/nope.md"]:
        resp = await client.get(
            f"/api/v1/repos/{repo_id}/workflow/document",
            params={"path": bad}, headers=AUTH,
        )
        assert resp.status_code == 404, bad
