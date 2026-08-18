"""Verify-URLs are derived from the candidate diff and the real router.

A surface is advertised only when its component or route declaration changed,
and its full route is resolved from the router (nesting included). The target
dev server need not already be running; the urls are projected onto the human
queue for the owner to follow when they are ready to verify.
"""

import json
import socket
import subprocess
import sys

from app.worker import run_pass
from tests.conftest import AUTH
from tests.features.runs.test_dispatch import _git_repo, _run_on

COMPONENTS = {
    "apps/web/src/features/development/Dev.tsx": "export function Dev() { return null }\n",
    "apps/web/src/features/development/Lake.tsx": "export function Lake() { return null }\n",
    "apps/web/src/features/runs/Inbox.tsx": "export function Inbox() { return null }\n",
    "apps/web/src/features/runs/RunDetail.tsx": "export function RunDetailPage() { return null }\n",
}
PORT = 5175

APP_TSX = """
import { Dev } from './features/development/Dev'
import { Lake } from './features/development/Lake'
import { Inbox } from './features/runs/Inbox'
import { RunDetailPage } from './features/runs/RunDetail'

export function App() {
  return (
    <Routes>
      <Route path="development" element={<Dev />}>
        <Route path="lake" element={<Lake />} />
      </Route>
      <Route path="inbox" element={<Inbox />} />
      <Route path="runs/:id" element={<RunDetailPage />} />
    </Routes>
  )
}
"""


def _install_web_app(repo_dir, port: int) -> None:
    web = repo_dir / "apps" / "web"
    (web / "src").mkdir(parents=True)
    (web / "vite.config.js").write_text(f"export default {{ server: {{ port: {port} }} }}\n")
    (web / "src" / "App.tsx").write_text(APP_TSX)
    for rel, body in COMPONENTS.items():
        path = repo_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo_dir), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "web app"],
        check=True,
    )


def _agent_touching(*files):
    edits = ";".join(f"open({f!r},'a').write('// changed\\n')" for f in files)

    def command(_role, _provider, _task, _repo_path):
        return [sys.executable, "-c", f"{edits};print('SUMMARY: changed pages')"]

    return command


def _agent_changing_route(old: str, new: str):
    script = (
        "from pathlib import Path;"
        "path=Path('apps/web/src/App.tsx');"
        f"path.write_text(path.read_text().replace({old!r}, {new!r}));"
        "print('SUMMARY: changed route')"
    )

    def command(_role, _provider, _task, _repo_path):
        return [sys.executable, "-c", script]

    return command


async def _verify_urls(client, run_id):
    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    arts = [a for a in detail["artifacts"] if a["kind"] == "verification"]
    return json.loads(arts[-1]["content"])["urls"] if arts else None


async def _build(
    db, client, tmp_path, monkeypatch, *touched, command=None, port=PORT
):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_web_app(repo_dir, port)
    run_id = await _run_on(client, repo_dir)
    monkeypatch.setattr("app.worker._agent_command", command or _agent_touching(*touched))
    assert await run_pass(db, run_id, "builder", "stub") == "done"
    return run_id


async def test_changed_page_becomes_its_full_route_url(db, client, tmp_path, monkeypatch):
    run_id = await _build(
        db, client, tmp_path, monkeypatch,
        "apps/web/src/features/development/Lake.tsx",
    )
    assert await _verify_urls(client, run_id) == [
        f"http://localhost:{PORT}/development/lake"
    ]


async def test_an_unchanged_route_is_never_advertised(db, client, tmp_path, monkeypatch):
    # Only Lake changed; /inbox (Inbox.tsx) is untouched and must not appear.
    run_id = await _build(
        db, client, tmp_path, monkeypatch,
        "apps/web/src/features/development/Lake.tsx",
    )
    assert f"http://localhost:{PORT}/inbox" not in await _verify_urls(
        client, run_id
    )


async def test_a_parameterised_route_is_skipped(db, client, tmp_path, monkeypatch):
    # RunDetail renders /runs/:id — no concrete destination, so no url.
    run_id = await _build(
        db, client, tmp_path, monkeypatch,
        "apps/web/src/features/runs/RunDetail.tsx",
    )
    assert await _verify_urls(client, run_id) == []


async def test_two_changed_surfaces_yield_two_urls(db, client, tmp_path, monkeypatch):
    run_id = await _build(
        db, client, tmp_path, monkeypatch,
        "apps/web/src/features/development/Lake.tsx",
        "apps/web/src/features/runs/Inbox.tsx",
    )
    assert set(await _verify_urls(client, run_id)) == {
        f"http://localhost:{PORT}/development/lake",
        f"http://localhost:{PORT}/inbox",
    }


async def test_a_route_only_edit_yields_the_new_destination(
    db, client, tmp_path, monkeypatch
):
    run_id = await _build(
        db,
        client,
        tmp_path,
        monkeypatch,
        command=_agent_changing_route('path="inbox"', 'path="queue"'),
    )
    assert await _verify_urls(client, run_id) == [
        f"http://localhost:{PORT}/queue"
    ]


async def test_a_changed_surface_link_does_not_require_a_running_dev_server(
    db, client, tmp_path, monkeypatch
):
    with socket.socket() as unused_socket:
        unused_socket.bind(("127.0.0.1", 0))
        closed_port = unused_socket.getsockname()[1]
    run_id = await _build(
        db, client, tmp_path, monkeypatch,
        "apps/web/src/features/development/Lake.tsx",
        port=closed_port,
    )
    assert await _verify_urls(client, run_id) == [
        f"http://localhost:{closed_port}/development/lake"
    ]


async def test_human_queue_projects_the_verify_urls(db, client, tmp_path, monkeypatch):
    run_id = await _build(
        db, client, tmp_path, monkeypatch,
        "apps/web/src/features/development/Lake.tsx",
    )

    async def post(path, body):
        return await client.post(f"/api/v1/runs/{run_id}{path}", json=body, headers=AUTH)

    await post("/claim", {"role": "reviewer", "holder": "stub"})
    await post(
        "/events",
        {"type": "reviewer_findings_posted", "actor": "reviewer",
         "payload": {"verdict": "pass"}},
    )

    items = (await client.get("/api/v1/queue/human", headers=AUTH)).json()
    item = next(i for i in items if i["run"]["id"] == run_id)
    assert item["verify_urls"] == [
        f"http://localhost:{PORT}/development/lake"
    ]
