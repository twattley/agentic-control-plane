"""Truncation must not eat an instruction the fix round needs (acp-033).

Two failure modes: gate output that keeps the banner head and drops the
failing tests from the tail, and any over-budget cut landing silently
mid-word. Every bound stays a bound; every cut becomes visible.
"""

from app.worker import _GATE_CHARS, _clip, _summary, run_pass
from tests.features.runs.test_close_delegation import _install_closer
from tests.features.runs.test_dispatch import (
    _drive_to_closing,
    _gate_event,
    _git_repo,
    _run_on,
    _state,
)


def test_clip_under_budget_is_untouched_and_unmarked():
    assert _clip("all good", 100) == "all good"
    assert _clip("  padded  ", 100) == "padded"


def test_clip_head_cut_lands_on_whitespace_and_is_marked():
    out = _clip("word " * 300, 100)

    assert out.endswith("[… truncated]")
    body = out[: -len(" [… truncated]")]
    assert body.endswith("word")  # whole word, not "wor"
    assert len(out) <= 100 + len(" [… truncated]")


def test_clip_tail_keeps_the_end_and_marks_the_missing_head():
    tail = "FAILED tests/test_x.py::test_y - assert 1 == 2"
    out = _clip(("banner " * 100) + tail, 120, keep_tail=True)

    assert out.startswith("[truncated …]")
    assert out.endswith(tail)
    # The kept body starts on a whole token, never mid-word.
    assert out[len("[truncated …] "):].startswith("banner ")


def test_gate_budget_holds_a_real_short_summary_block():
    """acp-033 raised the gate budget so pytest's short-summary block fits
    whole; a ~1200-char trailing block must survive intact."""
    block = "".join(f"FAILED tests/test_mod.py::test_case_{i} - boom\n" for i in range(26))
    assert 1000 < len(block) < _GATE_CHARS
    out = _clip(("banner-line\n" * 400) + block, _GATE_CHARS, keep_tail=True)

    assert block.strip() in out


def test_clip_bounds_a_pathological_payload_both_ways():
    huge = "x" * 2_000_000
    assert len(_clip(huge, 500)) <= 500 + len(" [… truncated]")
    assert len(_clip(huge, 500, keep_tail=True)) <= 500 + len("[truncated …] ")


def test_reviewer_summary_over_budget_is_marked_not_beheaded():
    out = _summary(("finding " * 700).strip(), "codex", "reviewer")

    assert out.endswith("[… truncated]")
    assert len(out) <= 4000 + len(" [… truncated]")


def test_reviewer_summary_under_budget_carries_no_marker():
    message = "1. worker.py:12 - fix the loop. VERDICT: changes"
    assert _summary(message, "codex", "reviewer") == message


async def test_failed_inline_gate_keeps_the_tail_not_the_banner(db, client, tmp_path):
    """The head of a failing test run is the platform banner; the failing
    tests live at the end. Since acp-016 this summary is the fix round's
    instruction, so the tail is the half that must survive."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    gate = (
        "i=0; while [ $i -lt 300 ]; do echo banner-line-$i; i=$((i+1)); done; "
        "echo FAILED short summary tail; exit 1"
    )
    run_id = await _run_on(client, repo_dir, gate=gate)
    await _drive_to_closing(client, run_id)

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    event = await _gate_event(client, run_id)
    assert event["type"] == "gate_failed"
    summary = event["payload"]["summary"]
    assert "FAILED short summary tail" in summary
    assert summary.startswith("[truncated …]")
    assert "banner-line-5\n" not in summary  # the head is the dropped end


async def test_refusing_closer_keeps_the_tail_of_its_output(db, client, tmp_path):
    """The real closer's gate log lands on stdout and its refusal reason is a
    one-line SystemExit on stderr — the reason must be the surviving end."""
    repo_dir = tmp_path / "repo"
    _git_repo(repo_dir)
    _install_closer(
        repo_dir, exit_code=1,
        stdout=("gate-log-line " * 400).strip(),
        stderr="REFUSED: close requires review-loop",
    )
    run_id = await _run_on(client, repo_dir, gate="uv run pytest")
    await _drive_to_closing(client, run_id)
    (repo_dir / "feature.py").write_text("VALUE = 1\n")

    assert await run_pass(db, run_id, "closer", "system") == "done"

    assert await _state(client, run_id) == "needs_work"
    summary = (await _gate_event(client, run_id))["payload"]["summary"]
    assert "REFUSED: close requires review-loop" in summary
    assert summary.startswith("[truncated …]")
