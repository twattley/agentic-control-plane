"""A data slice's verification artifact carries a real captured preview.

The builder captures an HTML preview by RUNNING its code and writes it, next to
the exact command that produced it, to `.agent-artifacts/<run_id>.preview.json`.
The worker lifts that record out of the checkout — so it never reaches the diff
or the commit — and folds it into the run's `verification` artifact next to the
derived URLs.

File existence is not treated as proof. The worker clears any same-run file
before dispatch (freshness), refuses a record with no `source`/`html`
provenance, and exposes `source` for the reviewer to check against the diff.
Oversized output is truncated at whole rows rather than dumped.
"""

import json
import subprocess
import sys
from types import SimpleNamespace

from app.worker import _MAX_PREVIEW_CHARS, _task_for, run_pass
from tests.conftest import AUTH
from tests.features.runs.test_dispatch import _git_repo, _run_on


def _detail(run_id=7, events=(), artifacts=()):
    run = SimpleNamespace(id=run_id, ticket_id="SBX-3", title="Preview it", mode="direct")
    return SimpleNamespace(run=run, events=list(events), artifacts=list(artifacts))


def _verification_artifact(preview):
    return SimpleNamespace(
        kind="verification",
        content=json.dumps({"urls": [], "data_preview": preview}),
    )

HEAD_TABLE = (
    "<table><thead><tr><th>id</th><th>name</th></tr></thead>"
    "<tbody><tr><td>1</td><td>ada</td></tr></tbody></table>\nrows: 3, nulls: 0\n"
)


def _agent_writing_preview(run_id: int, record: dict, *, also_edit: bool = False):
    """A fake builder that captures a preview file DURING its pass.

    This models the real contract: the preview is produced by the agent while
    it runs, not pre-planted, so it survives the worker's clear-before-dispatch.
    """
    payload = json.dumps(record)

    def command(_role, _provider, _task, _repo_path):
        lines = [
            "import os",
            "os.makedirs('.agent-artifacts', exist_ok=True)",
            f"open('.agent-artifacts/{run_id}.preview.json','w').write({payload!r})",
        ]
        if also_edit:
            lines.append("open('README.md','a').write('\\nedit\\n')")
        lines.append("print('SUMMARY: wrote preview')")
        return [sys.executable, "-c", ";".join(lines)]

    return command


async def _verification(client, run_id):
    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    for artifact in reversed(detail["artifacts"]):
        if artifact["kind"] == "verification":
            return json.loads(artifact["content"]), detail
    return None, detail


async def _preview(client, run_id):
    content, _ = await _verification(client, run_id)
    return content.get("data_preview") if content else None


async def test_a_data_slice_shows_a_captured_preview(db, client, tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    record = {"source": "python scripts/etl.py --preview", "html": HEAD_TABLE}
    monkeypatch.setattr("app.worker._agent_command", _agent_writing_preview(run_id, record))

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    preview = await _preview(client, run_id)
    assert preview is not None
    assert "rows: 3, nulls: 0" in preview["html"]
    assert preview["source"] == "python scripts/etl.py --preview"
    assert preview["truncated"] is False
    # lifted out of the checkout — evidence's invariant, reused
    assert not (repo_dir / ".agent-artifacts" / f"{run_id}.preview.json").exists()


async def test_no_preview_file_means_no_data_preview(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    # the verification artifact still exists (for urls); its preview is null
    content, _ = await _verification(client, run_id)
    assert content is not None
    assert content["data_preview"] is None


async def test_a_stale_same_run_preview_is_not_published(db, client, tmp_path):
    """A file left before this pass (e.g. a crashed earlier pass) is not proof.

    The plain stub builder captures no preview. The pre-planted file must be
    cleared before dispatch, so the published preview is null.
    """
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    stale = repo_dir / ".agent-artifacts" / f"{run_id}.preview.json"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text(json.dumps({"source": "stale", "html": HEAD_TABLE}))

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    assert await _preview(client, run_id) is None


async def test_a_preview_without_provenance_is_surfaced_as_invalid(
    db, client, tmp_path, monkeypatch
):
    """A record with no `source` is a blob, not a capture — but a file that IS
    present and defective must be surfaced, not silently dropped into "no
    preview" where a broken capture hides behind an honest empty state."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    record = {"html": HEAD_TABLE}  # no source: existence is not provenance
    monkeypatch.setattr("app.worker._agent_command", _agent_writing_preview(run_id, record))

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    preview = await _preview(client, run_id)
    assert preview is not None  # not swallowed
    assert "source" in preview["error"]
    assert "html" not in preview  # never published as a viewable table


async def test_a_malformed_capture_is_surfaced_not_dropped(db, client, tmp_path, monkeypatch):
    """A present-but-unparseable file is an explicit error, distinct from the
    optional no-file path."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    def command(_role, _provider, _task, _repo_path):
        return [sys.executable, "-c", (
            "import os;"
            "os.makedirs('.agent-artifacts', exist_ok=True);"
            f"open('.agent-artifacts/{run_id}.preview.json','w').write('not json at all');"
            "print('SUMMARY: broken capture')"
        )]

    monkeypatch.setattr("app.worker._agent_command", command)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    preview = await _preview(client, run_id)
    assert preview is not None
    assert "JSON" in preview["error"]


def test_reviewer_prompt_shows_the_preview_source(tmp_path):
    """Finding #1: the promised reviewer control is real — the source the builder
    claims produced the table reaches the reviewer to check against the diff."""
    preview = {
        "html": HEAD_TABLE, "source": "python scripts/etl.py --preview", "truncated": False,
    }
    detail = _detail(artifacts=[_verification_artifact(preview)])
    task = _task_for(detail, "reviewer", str(tmp_path))

    assert "python scripts/etl.py --preview" in task  # the reviewer can see it
    assert "corresponds to code in the diff" in task
    assert "VERDICT: changes" in task  # an untied source is a changes verdict


def test_reviewer_prompt_has_no_preview_note_without_a_preview(tmp_path):
    task = _task_for(_detail(), "reviewer", str(tmp_path))

    assert "DATA PREVIEW" not in task


async def test_oversized_preview_is_truncated_legibly(db, client, tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    rows = "".join(f"<tr><td>{i}</td></tr>" for i in range(_MAX_PREVIEW_CHARS))
    big = (
        "<table><tbody><tr><td>HEADMARK</td></tr>"
        + rows
        + "<tr><td>TAILMARK</td></tr></tbody></table>"
    )
    record = {"source": "python dump.py", "html": big}
    monkeypatch.setattr("app.worker._agent_command", _agent_writing_preview(run_id, record))

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    preview = await _preview(client, run_id)
    html = preview["html"]
    assert preview["truncated"] is True
    assert len(html) <= _MAX_PREVIEW_CHARS
    # head and tail rows survive; the middle is elided, not dumped or lied about
    assert "HEADMARK" in html
    assert "TAILMARK" in html
    assert "truncated" in html.lower()
    # the cut lands on whole rows: no dangling opening cell tag was left behind
    assert html.count("<td") == html.count("</td>")


async def test_data_preview_never_reaches_the_diff(db, client, tmp_path, monkeypatch):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    record = {"source": "python scripts/etl.py --preview", "html": HEAD_TABLE}
    monkeypatch.setattr(
        "app.worker._agent_command",
        _agent_writing_preview(run_id, record, also_edit=True),
    )

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    _, detail = await _verification(client, run_id)
    diff = next((a["content"] for a in detail["artifacts"] if a["kind"] == "diff"), "")
    assert "edit" in diff  # the real change is captured
    assert ".preview.json" not in diff  # the preview is not
    status = subprocess.run(
        ["git", "-C", str(repo_dir), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert ".preview.json" not in status
