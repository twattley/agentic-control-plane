"""Optional evidence artifact: a builder may leave a markdown case table in
`.agent-artifacts/<run_id>.md`. The worker attaches it and removes the file, so
evidence reaches the reviewer without ever reaching the commit."""

import subprocess
from types import SimpleNamespace

import pytest

from app.features.runs.models import ArtifactIn
from app.worker import _task_for, run_pass
from tests.conftest import AUTH

CASES = "| input | expected | actual |\n|---|---|---|\n| 2 | 4 | 4 |\n"


def _git_repo(path):
    path.mkdir()
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / "README.md").write_text("# repo\n")
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init"],
        check=True,
    )


async def _run_on(client, repo_path) -> int:
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "tmp", "name": "tmp", "path": str(repo_path)},
        headers=AUTH,
    )).json()["id"]
    return (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo"},
        headers=AUTH,
    )).json()["id"]


async def _drive_to_approved(db, client, run_id: int) -> None:
    """Walk the state machine to `approved` so the closer pass can run."""
    await run_pass(db, run_id, "builder", "stub")
    await client.post(
        f"/api/v1/runs/{run_id}/claim",
        json={"role": "reviewer", "holder": "stub"}, headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/events",
        json={"type": "reviewer_findings_posted", "actor": "reviewer",
              "payload": {"verdict": "pass"}},
        headers=AUTH,
    )
    await client.post(
        f"/api/v1/runs/{run_id}/decision", json={"decision": "approve"}, headers=AUTH
    )


async def _artifacts(client, run_id: int) -> list[dict]:
    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    return detail["artifacts"]


async def test_evidence_file_becomes_an_artifact_and_leaves_the_checkout(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    evidence = repo_dir / ".agent-artifacts" / f"{run_id}.md"
    evidence.parent.mkdir()
    evidence.write_text(CASES)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    artifacts = await _artifacts(client, run_id)
    stored = next(a for a in artifacts if a["kind"] == "evidence")
    assert "| 2 | 4 | 4 |" in stored["content"]
    assert not evidence.exists()  # removed from the checkout


async def test_evidence_never_reaches_the_diff(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    evidence = repo_dir / ".agent-artifacts" / f"{run_id}.md"
    evidence.parent.mkdir()
    evidence.write_text(CASES)

    await run_pass(db, run_id, "builder", "stub")

    diff = next(a for a in await _artifacts(client, run_id) if a["kind"] == "diff")
    assert ".agent-artifacts" not in diff["content"]


async def test_a_stale_evidence_file_never_reaches_the_diff(db, client, tmp_path):
    """Evidence from a crashed earlier pass is not this run's to capture, but it
    is still the artifact directory — `git add -A` must not sweep it up."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    stale = repo_dir / ".agent-artifacts" / "previous-run.md"
    stale.parent.mkdir()
    stale.write_text(CASES)

    await run_pass(db, run_id, "builder", "stub")

    diff = next(a for a in await _artifacts(client, run_id) if a["kind"] == "diff")
    assert ".agent-artifacts" not in diff["content"]


async def test_pre_staged_evidence_never_reaches_the_diff(db, client, tmp_path):
    """An agent may stage its work before returning. Capturing the evidence
    must remove it from both the checkout and the existing Git index entry."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    evidence = repo_dir / ".agent-artifacts" / f"{run_id}.md"
    evidence.parent.mkdir()
    evidence.write_text(CASES)
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)

    await run_pass(db, run_id, "builder", "stub")

    diff = next(a for a in await _artifacts(client, run_id) if a["kind"] == "diff")
    assert ".agent-artifacts" not in diff["content"]


async def test_the_closer_commits_without_the_artifact_directory(db, client, tmp_path):
    """The last `git add -A` in the pipeline is the closer's. Evidence must not
    ride into the commit there either."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    stale = repo_dir / ".agent-artifacts" / "previous-run.md"
    stale.parent.mkdir()
    stale.write_text(CASES)

    await _drive_to_approved(db, client, run_id)
    await client.post(
        f"/api/v1/runs/{run_id}/decision", json={"decision": "close"}, headers=AUTH
    )
    await run_pass(db, run_id, "closer", "stub")

    committed = subprocess.run(
        ["git", "-C", str(repo_dir), "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert ".agent-artifacts" not in committed


async def test_the_closer_unstages_the_artifact_directory(db, client, tmp_path):
    """The closer must remove evidence already present in the index, not only
    exclude untracked evidence from its own `git add`."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)
    await _drive_to_approved(db, client, run_id)
    stale = repo_dir / ".agent-artifacts" / "previous-run.md"
    stale.parent.mkdir()
    stale.write_text(CASES)
    subprocess.run(["git", "-C", str(repo_dir), "add", "-A"], check=True)

    await client.post(
        f"/api/v1/runs/{run_id}/decision", json={"decision": "close"}, headers=AUTH
    )
    await run_pass(db, run_id, "closer", "stub")

    committed = subprocess.run(
        ["git", "-C", str(repo_dir), "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout
    assert ".agent-artifacts" not in committed


async def test_a_pass_without_evidence_is_unchanged(db, client, tmp_path):
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    run_id = await _run_on(client, repo_dir)

    assert await run_pass(db, run_id, "builder", "stub") == "done"

    kinds = [a["kind"] for a in await _artifacts(client, run_id)]
    assert "evidence" not in kinds
    assert "diff" in kinds


def _detail(run_id=7, events=(), artifacts=()):
    run = SimpleNamespace(id=run_id, ticket_id="SBX-3", title="Do the thing", mode="direct")
    return SimpleNamespace(run=run, events=list(events), artifacts=list(artifacts))


async def test_artifact_kind_is_a_closed_contract(client, db):
    """domain-types declares a closed union; the Python side is the source of
    truth and must say the same thing, at the API boundary and in the schema."""
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "kinds", "name": "kinds", "path": "/p"}, headers=AUTH,
    )).json()["id"]
    run_id = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": "t1", "title": "demo"}, headers=AUTH,
    )).json()["id"]

    rejected = await client.post(
        f"/api/v1/runs/{run_id}/artifacts",
        json={"kind": "not-a-kind", "content": "x"}, headers=AUTH,
    )
    accepted = await client.post(
        f"/api/v1/runs/{run_id}/artifacts",
        json={"kind": "evidence", "content": CASES}, headers=AUTH,
    )

    assert rejected.status_code == 422
    assert accepted.status_code < 300
    assert set(ArtifactIn.model_json_schema()["properties"]["kind"]["enum"]) == {
        "diff", "test_output", "screenshot", "log", "evidence",
        "revision_base", "revision_diff", "verification",
    }


_FINDINGS = SimpleNamespace(
    type="reviewer_findings_posted", payload={"summary": "fix the loop"}
)


@pytest.mark.parametrize("events", [(), (_FINDINGS,)], ids=["first-pass", "fix-pass"])
def test_builder_prompt_invites_evidence_without_demanding_it(tmp_path, events):
    """The invitation must stay an invitation. A pass with nothing worth
    demonstrating writes nothing and is still complete — wording that pressures
    a refactor into inventing a case table is the failure this pins."""
    task = _task_for(_detail(events=events), "builder", str(tmp_path))

    assert ".agent-artifacts/7.md" in task
    assert "Optional" in task
    assert "actual" in task.lower()          # real outputs, not claims
    assert "Write nothing" in task           # opting out is explicit...
    assert "still a complete pass" in task   # ...and costs the builder nothing


def test_reviewer_prompt_shows_evidence_and_distrusts_unrun_claims(tmp_path):
    evidence = SimpleNamespace(kind="evidence", content=CASES)
    task = _task_for(_detail(artifacts=[evidence]), "reviewer", str(tmp_path))

    assert "| 2 | 4 | 4 |" in task           # the reviewer can see it
    assert "VERDICT: changes" in task
    assert "could not have been run" in task  # unrun claims are a changes verdict


def test_reviewer_prompt_unchanged_without_evidence(tmp_path):
    task = _task_for(_detail(), "reviewer", str(tmp_path))

    assert "EVIDENCE" not in task
    assert "VERDICT" in task
