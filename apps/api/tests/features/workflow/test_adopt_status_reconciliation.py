"""Adopting a legacy ticket must produce exactly one `## Status` block (acp-014).

The portable tools read the FIRST status match in the file, so a second block —
the legacy body's own — is not clutter but active misinformation: S001's close
read the stale skeleton block while the real state sat below it. The incoming
status is reconciled into the skeleton's block, never appended beside it."""

from tests.conftest import AUTH
from tests.features.workflow.test_story_authoring import _install_tool, _repo

LEGACY_WITH_HISTORY = """# Clean up the parser

## Status

- State: ready
- Phase: review-ready
- Started: 2026-08-01
- Updated: 2026-08-02
- Completed: —
- Last: builder finished, awaiting review
- Next: review

## Story

Drop the dead branches in the parser.
"""


async def _adopted_text(client, tmp_path) -> str:
    _install_tool(tmp_path)
    legacy = tmp_path / "tickets" / "old-cleanup.md"
    legacy.parent.mkdir(exist_ok=True)
    legacy.write_text(LEGACY_WITH_HISTORY)
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/adopt",
        json={"legacy_id": "old-cleanup", "epic_id": "E001", "coordination_class": "feature"},
        headers=AUTH,
    )
    assert resp.status_code == 201
    return (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").read_text()


async def test_adopted_story_has_exactly_one_status_block(db, client, tmp_path):
    text = await _adopted_text(client, tmp_path)
    assert text.count("## Status") == 1
    assert "Drop the dead branches in the parser." in text  # body still moved in


async def test_adoption_carries_history_but_not_legacy_lifecycle(db, client, tmp_path):
    """Started is a fact worth keeping. State/Phase are not: the story re-enters
    the lifecycle at backlog, and legacy phase vocabulary ('review-ready') is
    exactly what the portable closer rejects."""
    text = await _adopted_text(client, tmp_path)

    assert "- Started: 2026-08-01" in text     # history carried into the skeleton
    assert "- State: backlog" in text          # lifecycle restarts where the file lives
    assert "- Phase: shape" in text
    assert "review-ready" not in text          # legacy vocabulary does not survive
    assert "- Completed: —" in text            # placeholder intact for the closer


async def test_fenced_status_example_is_documentation_not_status(db, client, tmp_path):
    """The portable contract blanks fenced blocks before reading status —
    an example of the format is prose about it, not an instance of it. The
    merge must make the same distinction or it eats the example and everything
    to the next heading."""
    _install_tool(tmp_path)
    legacy = tmp_path / "tickets" / "old-cleanup.md"
    legacy.parent.mkdir(exist_ok=True)
    legacy.write_text(
        "# Clean up the parser\n\n## Story\n\nDocument the block:\n\n"
        "```markdown\n## Status\n\n- State: example\n```\n\n"
        "## Notes\n\nKeep this section.\n"
    )
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/adopt",
        json={"legacy_id": "old-cleanup", "epic_id": "E001", "coordination_class": "feature"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    text = (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").read_text()
    assert "- State: example" in text        # the fenced example survives intact
    assert "Keep this section." in text      # and nothing after it was eaten
    assert text.count("## Status") == 2      # skeleton's block + the fenced example
    assert "- State: backlog" in text        # the real block is still the skeleton's


async def test_backslashes_in_carried_history_survive_reconciliation(db, client, tmp_path):
    r"""A carried value is data, not replacement syntax — 'C:\work' in a
    Started line must not raise out of the adopt."""
    _install_tool(tmp_path)
    legacy = tmp_path / "tickets" / "old-cleanup.md"
    legacy.parent.mkdir(exist_ok=True)
    legacy.write_text(
        "# Clean up the parser\n\n## Status\n\n"
        "- Started: 2026-08-01 \\g<oops>\n\n## Story\n\nBody.\n"
    )
    repo_id = await _repo(client, tmp_path)

    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories/adopt",
        json={"legacy_id": "old-cleanup", "epic_id": "E001", "coordination_class": "feature"},
        headers=AUTH,
    )

    assert resp.status_code == 201
    text = (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").read_text()
    assert "- Started: 2026-08-01 \\g<oops>" in text


async def test_shaped_body_with_its_own_status_cannot_add_a_second_block(db, client, tmp_path):
    """The freeze path has the same exposure: a shaping agent that emits a
    Status section must not end up beside the skeleton's."""
    _install_tool(tmp_path)
    repo_id = await _repo(client, tmp_path)

    body = "## Status\n\n- State: shaped\n\n## Story\n\nShaped outcome.\n"
    resp = await client.post(
        f"/api/v1/repos/{repo_id}/workflow/stories",
        json={"epic_id": "E001", "coordination_class": "feature",
              "title": "Do a thing", "body": body},
        headers=AUTH,
    )

    assert resp.status_code == 201
    text = (tmp_path / "tickets" / "backlog" / "E001-S00-do-a-thing.md").read_text()
    assert text.count("## Status") == 1
    assert "- State: backlog" in text
    assert "- State: shaped" not in text
    assert "Shaped outcome." in text
