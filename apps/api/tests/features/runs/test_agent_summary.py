"""What survives of an agent's final message into its event payload.

The reviewer's summary is not a headline: it is the entire instruction the fix
round receives (`_INSTRUCTION_SOURCES['reviewer_findings_posted']`). Findings
that name a file, a line and a change do not fit in a builder brief's budget.
"""

from app.worker import _headline, _summary

FINDING = (
    "apps/api/app/worker.py:142 - the summary is capped before it reaches the "
    "payload, so the fix round never sees this finding. Change: cap the "
    "reviewer branch separately from the builder brief.\n"
)


def test_a_located_findings_list_reaches_the_fix_round_whole():
    """Three located findings run past the old 500-character cap. Losing the
    tail silently is the failure this budget exists to prevent."""
    message = f"1. {FINDING}2. {FINDING}3. {FINDING}VERDICT: changes"
    assert len(message) > 500  # the case is only meaningful above the old cap

    assert _summary(message, "codex", "reviewer") == message


def test_a_builder_brief_stays_headline_sized():
    """The brief is a board caption, not an instruction. It keeps its budget."""
    summary = _summary("x" * 900, "codex", "builder")

    assert len(summary) == 500


def test_a_silent_agent_still_says_something():
    assert _summary("   ", "stub", "reviewer") == "stub reviewer pass complete"


def test_a_reviewer_message_is_still_bounded():
    assert len(_summary("x" * 20_000, "codex", "reviewer")) == 4000


def test_claude_json_is_unwrapped_before_the_budget_applies():
    """A claude payload's JSON envelope must not eat the findings' budget."""
    stdout = '{"result": "' + "x" * 700 + '"}'

    assert _summary(stdout, "claude", "reviewer") == "x" * 700


def test_builder_headline_is_the_deliberate_first_line():
    assert _headline(
        "SUMMARY: Add three loading dots\n\nLong implementation detail."
    ) == "Add three loading dots"


def test_builder_headline_finds_summary_after_a_handoff_preamble():
    assert _headline(
        "Everything passes and is ready for review.\n\n"
        "SUMMARY: Add three loading dots\n\nNext step: review it."
    ) == "Add three loading dots"
