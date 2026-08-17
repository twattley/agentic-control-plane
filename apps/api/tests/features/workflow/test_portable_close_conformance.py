"""A ticket the plane authors and drives must satisfy the portable contract at
every step (acp-014).

Every other test on both sides reads a fixture written by the same system that
parses it — which is how 138 green tests here and 141 in agentic-engineering
coexisted with a ticket format the two systems disagreed on. This file pins the
contract from the outside: the REAL portable kit's tools do the claiming and
closing, so a vocabulary change on either side fails here instead of surfacing
as hand repairs at the end of a lap."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

from app.config import settings
from app.features.workflow import repository as workflow_repo
from app.features.workflow.models import CompactIn, StoryCreateIn
from app.worker import _STATUS_FIELDS, REVIEW_PHASE, run_pass
from tests.conftest import AUTH

#: Where the canonical kit checkout lives. Overridable so a machine with an
#: unusual layout can still run the only cross-system check; ACP_REQUIRE_PORTABLE_KIT=1
#: turns absence into a failure instead of a skip, so losing this coverage is a
#: deliberate choice — never a silent side effect of a moved folder.
KIT_SCRIPTS = Path(
    os.environ.get(
        "ACP_PORTABLE_KIT", str(Path(settings.projects_root) / "agentic-engineering")
    )
) / "scripts"

pytestmark = pytest.mark.skipif(
    not KIT_SCRIPTS.is_dir() and os.environ.get("ACP_REQUIRE_PORTABLE_KIT") != "1",
    reason="portable kit checkout not present (ACP_PORTABLE_KIT to point at it, "
    "ACP_REQUIRE_PORTABLE_KIT=1 to fail instead of skip)",
)

CONTRACT_MARKER = "- `ticket_contract`: `epic-story-v1`"


def _kit_repo(tmp_path: Path) -> Path:
    """A git repo with the portable kit installed the way production repos have
    it: scripts symlinked to the canonical checkout, contract marker adopted."""
    repo = tmp_path / "conformance"
    (repo / "tickets").mkdir(parents=True)
    (repo / "tickets" / "README.md").write_text(f"# Tickets\n\n## Contract\n\n{CONTRACT_MARKER}\n")
    scripts = repo / "scripts"
    scripts.mkdir()
    for name in ("agent_workflow", "ticket_contract.py", "close_ticket"):
        (scripts / name).symlink_to(KIT_SCRIPTS / name)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "-m", "init"],
        check=True,
    )
    return repo


def _kit(repo: Path, *argv: str) -> dict:
    result = subprocess.run(
        [str(repo / "scripts" / "agent_workflow"), *argv],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, f"{argv}: {result.stderr or result.stdout}"
    return json.loads(result.stdout) if result.stdout.strip() else {}


def _kit_contract():
    """The portable parser itself — the same module close_ticket imports, not a
    copy of its regexes."""
    spec = importlib.util.spec_from_file_location(
        "kit_ticket_contract", KIT_SCRIPTS / "ticket_contract.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_plane_vocabulary_is_the_portable_vocabulary():
    """The lines each side could change unilaterally, pinned against the real
    kit rather than copied strings: the phase the closer demands, and the field
    list the builder prompt tells the agent to preserve."""
    contract = _kit_contract()
    assert REVIEW_PHASE == contract.STORY_REVIEW_PHASE
    assert set(_STATUS_FIELDS) == set(contract.REQUIRED_STORY_STATUS_FIELDS)


def test_adopted_story_satisfies_the_portable_contract(tmp_path):
    repo = _kit_repo(tmp_path)
    legacy = repo / "tickets" / "old-fix-the-parser.md"
    legacy.write_text(
        "# Fix the parser\n\n## Status\n\n- State: ready\n- Phase: review-ready\n"
        "- Started: 2026-08-01\n- Updated: 2026-08-02\n- Completed: —\n"
        "- Last: builder finished\n- Next: review\n\n## Story\n\nDrop the dead branches.\n"
    )

    authored = workflow_repo.adopt_legacy(str(repo), "old-fix-the-parser", None, "feature")

    text = (repo / authored.path).read_text()
    assert text.count("## Status") == 1

    contract = _kit_contract()
    fields = contract.story_status_fields(text)
    assert set(contract.REQUIRED_STORY_STATUS_FIELDS) <= set(fields)
    assert fields["Phase"] in contract.STORY_PHASES
    assert fields["Started"] == "2026-08-01"

    # and the kit's own inventory reports the story clean
    projection = workflow_repo.load_workflow(str(repo))
    story = next(s for s in projection.stories if s.story_id == authored.story_id)
    assert story.diagnostic_codes == []


def _authored_ready_story(repo: Path, title: str):
    """Author through the plane and promote to ready — where a run can start."""
    authored = workflow_repo.create_story(str(repo), StoryCreateIn(
        epic_id=None, coordination_class="feature", title=title,
        body="## Story\n\nOne honest lap through both systems.\n",
    ))
    return workflow_repo.mark_ready(str(repo), authored.story_id)


def _kit_review_cycle(repo: Path, ready) -> Path:
    """The kit's claim/post cycle to a reviewer pass — what a protocol-following
    builder and reviewer do in the checkout during a run. The one instructed
    status transition is applied mechanically, from the same constant the
    plane's prompt uses. Returns the ticket's in-progress path."""
    claim = _kit(repo, "claim", ready.story_id, "builder",
                 "--agent", "conformance-builder", "--ticket", ready.path)
    run_id = claim["run"]["id"]
    ticket = repo / "tickets" / "in-progress" / Path(ready.path).name
    assert ticket.is_file()  # the kit's claim moved the lane

    # The review handoff the plane's worker instructs its builder to perform.
    text = ticket.read_text()
    text = text.replace("- Phase: queued", f"- Phase: {REVIEW_PHASE}", 1)
    text = text.replace("- Started: —", "- Started: 2026-08-17", 1)
    ticket.write_text(text)

    _kit(repo, "post-findings", run_id, "--json",
         json.dumps({"goal": "prove the lap", "changed_files": [], "focus_areas": []}))
    _kit(repo, "claim", ready.story_id, "reviewer",
         "--agent", "conformance-reviewer", "--ticket", f"tickets/in-progress/{ticket.name}")
    _kit(repo, "post-findings", run_id, "--json",
         json.dumps({"verdict": "pass", "issues": []}))
    return ticket


def test_plane_authored_story_closes_with_the_portable_closer(tmp_path):
    """The whole lap with no hand edits: plane authors and promotes, the kit
    claims and posts, and the portable closer accepts the file. Every S001
    repair would fail this test."""
    repo = _kit_repo(tmp_path)
    ready = _authored_ready_story(repo, "Prove the lap")
    ticket = _kit_review_cycle(repo, ready)

    close = subprocess.run(
        [str(repo / "scripts" / "close_ticket"), ready.story_id,
         "--gate-command", "true", "--no-compact"],
        cwd=repo, capture_output=True, text=True, check=False,
    )
    assert close.returncode == 0, close.stderr or close.stdout

    completed = repo / "tickets" / "complete" / ticket.name
    assert completed.is_file()
    final = completed.read_text()
    assert final.count("## Status") == 1
    fields = _kit_contract().story_status_fields(final)
    assert fields["State"] == "complete"
    assert fields["Phase"] == "done"
    assert fields["Completed"] not in ("", "—")


async def test_plane_close_runs_the_repos_real_closer_end_to_end(db, client, tmp_path):
    """The two-closers seam, closed (acp-016): a run driven through the plane's
    own state machine reaches `closed` AND the ticket ends stamped in
    `complete/` — gate, stamp, lane move, and commit, with no terminal step."""
    repo = _kit_repo(tmp_path)
    ready = _authored_ready_story(repo, "Prove the seam")
    story_id = ready.story_id

    # The run starts while the story is ready; the kit's claim (a
    # protocol-following builder's first act) moves it to in-progress after.
    repo_id = (await client.post(
        "/api/v1/repos",
        json={"slug": "conformance", "name": "Conformance", "path": str(repo),
              "close_gate_command": "test -f tickets/README.md"},
        headers=AUTH,
    )).json()["id"]
    run_id = (await client.post(
        "/api/v1/runs",
        json={"repo_id": repo_id, "ticket_id": story_id, "title": "Prove the seam"},
        headers=AUTH,
    )).json()["id"]
    ticket = _kit_review_cycle(repo, ready)

    async def post(path, body):
        await client.post(f"/api/v1/runs/{run_id}{path}", json=body, headers=AUTH)
    await post("/claim", {"role": "builder", "holder": "codex"})
    await post("/events", {"type": "builder_brief_posted", "actor": "builder"})
    await post("/claim", {"role": "reviewer", "holder": "claude"})
    await post("/events", {"type": "reviewer_findings_posted", "actor": "reviewer",
                           "payload": {"verdict": "pass"}})
    await post("/decision", {"decision": "approve"})
    await post("/decision", {"decision": "close"})

    assert await run_pass(db, run_id, "closer", "system") == "done"

    detail = (await client.get(f"/api/v1/runs/{run_id}", headers=AUTH)).json()
    assert detail["run"]["state"] == "closed"

    completed = repo / "tickets" / "complete" / ticket.name
    assert completed.is_file()
    assert not ticket.exists()
    fields = _kit_contract().story_status_fields(completed.read_text())
    assert fields["State"] == "complete"
    assert fields["Phase"] == "done"

    log = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True
    )
    assert story_id in log.stdout  # the plane committed after the closer

    # The commit carried the whole close — lane move included — leaving nothing
    # behind: a clean tree is the proof the stamp is in history, not just on disk.
    porcelain = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True
    )
    assert porcelain.stdout.strip() == ""
    shown = subprocess.run(
        ["git", "-C", str(repo), "show", "--name-only", "--format=", "HEAD"],
        capture_output=True, text=True,
    )
    assert f"tickets/complete/{ticket.name}" in shown.stdout

    event = next(e for e in reversed(detail["events"]) if e["type"] == "gate_passed")
    assert event["payload"]["gate_command"] == "test -f tickets/README.md"


def test_kit_compact_payload_matches_the_planes_mirror(tmp_path):
    """`CompactResult` mirrors `compact_completed`'s payload. Pinned against
    the real tool's output — not the fixture the plane wrote for itself — so a
    payload change in the kit fails here, not in the project view."""
    repo = _kit_repo(tmp_path)

    result = workflow_repo.compact(str(repo), CompactIn(before="2026-01-01", dry_run=True))

    # model_validate inside compact() is the shape assertion; the values just
    # confirm the flags reached the tool.
    assert result.dry_run is True
    assert result.compacted == []
