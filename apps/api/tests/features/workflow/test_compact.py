"""On-demand compaction (acp-016): the project view's route to the sweep that
previously existed only in a terminal. Delegates to the repo's own
`agent_workflow compact`; a dry run previews what would move."""

import json

from tests.conftest import AUTH

PAYLOAD = {
    "ledger_file": "docs/DONE.md",
    "compacted": [{
        "title": "Old thing", "completed": "2026-07-01",
        "path": "tickets/complete/S001-old-thing.md", "note": "closed",
    }],
    "archived_runs": ["abc123"],
    "preserved": ["tickets/complete/KEEP.md"],
    "stale_claims": ["def456"],
    "dry_run": True,
}


def _install_tool(repo, exit_code: int = 0) -> None:
    scripts = repo / "scripts"
    scripts.mkdir(exist_ok=True)
    command = scripts / "agent_workflow"
    command.write_text(
        "#!/bin/sh\n"
        'printf "%s\\n" "$*" >> args.log\n'
        f"if [ {exit_code} -ne 0 ]; then echo boom >&2; exit {exit_code}; fi\n"
        f"printf '%s\\n' '{json.dumps(PAYLOAD)}'\n"
    )
    command.chmod(0o755)


async def _repo(client, tmp_path) -> int:
    (tmp_path / "tickets").mkdir(exist_ok=True)
    resp = await client.post(
        "/api/v1/repos", json={"slug": "p", "name": "P", "path": str(tmp_path)}, headers=AUTH
    )
    return resp.json()["id"]


async def test_dry_run_previews_what_would_move(db, client, tmp_path):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/compact",
        json={"before": "2026-08-01", "dry_run": True},
        headers=AUTH,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["dry_run"] is True
    assert body["compacted"][0]["path"] == "tickets/complete/S001-old-thing.md"
    assert body["archived_runs"] == ["abc123"]
    assert body["stale_claims"] == ["def456"]
    argv = (tmp_path / "args.log").read_text().splitlines()[-1]
    assert argv.startswith("compact")
    assert "--before 2026-08-01" in argv
    assert "--dry-run" in argv


async def test_real_run_omits_the_dry_run_flag(db, client, tmp_path):
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/compact",
        json={"dry_run": False},
        headers=AUTH,
    )

    assert resp.status_code == 200
    argv = (tmp_path / "args.log").read_text().splitlines()[-1]
    assert "--dry-run" not in argv
    assert "--before" not in argv


async def test_compact_defaults_to_a_dry_run(db, client, tmp_path):
    """The destructive direction must be asked for; an empty body previews."""
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/compact", json={}, headers=AUTH
    )

    assert resp.status_code == 200
    assert "--dry-run" in (tmp_path / "args.log").read_text().splitlines()[-1]


async def test_compact_without_the_tool_conflicts(db, client, tmp_path):
    repo_id = await _repo(client, tmp_path)
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/compact", json={}, headers=AUTH
    )
    assert resp.status_code == 409


async def test_compact_tool_failure_is_502(db, client, tmp_path):
    _install_tool(tmp_path, exit_code=1)
    repo_id = await _repo(client, tmp_path)
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/compact", json={}, headers=AUTH
    )
    assert resp.status_code == 502
    assert "boom" in resp.json()["detail"]
