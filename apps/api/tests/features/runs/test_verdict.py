import json
from types import SimpleNamespace

import pytest

from app.services.state_machine import event_transition
from app.worker import _changes_since_last_human_word, _parse_verdict, _review_outcome


def test_parse_plain_pass():
    assert _parse_verdict("looks good\nVERDICT: pass", "codex") == "pass"


def test_parse_plain_changes():
    assert _parse_verdict("issues here\nVERDICT: changes: fix the off-by-one", "codex") == "changes"


def test_parse_claude_json_result():
    out = json.dumps({"result": "reviewed.\nVERDICT: changes needs a test"})
    assert _parse_verdict(out, "claude") == "changes"


def test_ambiguous_defaults_to_pass_to_escalate():
    assert _parse_verdict("hmm, not sure", "codex") == "pass"
    assert _parse_verdict("", "stub") == "pass"


def test_exhausting_the_rounds_escalates_without_rewriting_the_verdict():
    """The cap decides who acts next. It does not get to change what the
    reviewer said. Recording 'pass' over a rejection told the human the work
    was approved and let it satisfy a gate that requires a passing review."""
    outcome = _review_outcome("changes", prior_changes=2, cap=2)

    assert outcome.verdict == "changes"
    assert outcome.escalated is True


def test_a_rejection_within_the_rounds_is_not_escalated():
    outcome = _review_outcome("changes", prior_changes=1, cap=2)

    assert outcome.verdict == "changes"
    assert outcome.escalated is False


def test_a_genuine_pass_is_never_marked_escalated():
    outcome = _review_outcome("pass", prior_changes=5, cap=2)

    assert outcome.verdict == "pass"
    assert outcome.escalated is False


def test_an_escalated_rejection_counts_as_a_change_round():
    """Recording escalations as passes hid them from the round count, so a
    human bounce reset the budget and the loop could run past its cap. Now a
    run that has already escalated returns to the human on the next rejection
    instead of going round again."""
    already_escalated = _review_outcome("changes", prior_changes=2, cap=2)
    assert already_escalated.verdict == "changes"  # so the next count sees it

    next_round = _review_outcome("changes", prior_changes=3, cap=2)
    assert next_round.escalated is True


def test_a_human_note_resets_the_round_cap_after_an_escalation():
    """Run 4's shape: exhaust one disagreement, then let the human start a
    fresh instruction without immediately escalating its first rejection."""
    history = [
        SimpleNamespace(
            type="reviewer_findings_posted",
            actor="reviewer",
            payload={"verdict": "changes", "escalated": index == 3},
        )
        for index in range(4)
    ]
    history.append(SimpleNamespace(
        type="human_note_posted", actor="human", payload={"note": "new work"}
    ))

    prior_changes = _changes_since_last_human_word(history)
    outcome = _review_outcome("changes", prior_changes, cap=3)

    assert prior_changes == 0
    assert outcome.escalated is False


def test_the_round_cap_still_holds_without_a_new_human_word():
    history = [
        SimpleNamespace(
            type="reviewer_findings_posted",
            actor="reviewer",
            payload={"verdict": "changes", "escalated": index == 3},
        )
        for index in range(4)
    ]

    prior_changes = _changes_since_last_human_word(history)
    outcome = _review_outcome("changes", prior_changes, cap=3)

    assert prior_changes == 4
    assert outcome.escalated is True


@pytest.mark.parametrize("decision_event", ["human_approved", "close_requested", "blocked"])
def test_a_human_decision_also_starts_a_fresh_round_budget(decision_event):
    history = [
        SimpleNamespace(
            type="reviewer_findings_posted",
            actor="reviewer",
            payload={"verdict": "changes", "escalated": True},
        ),
        SimpleNamespace(type=decision_event, actor="human", payload={}),
    ]

    assert _changes_since_last_human_word(history) == 0


def test_an_escalated_rejection_still_routes_to_the_human():
    """The cap must keep working: the point of escalating is to stop bouncing
    the run between two models forever."""
    state = event_transition(
        "reviewing", "reviewer_findings_posted",
        {"verdict": "changes", "escalated": True},
    )

    assert state == "awaiting_human"


def test_an_ordinary_rejection_still_returns_to_the_builder():
    state = event_transition(
        "reviewing", "reviewer_findings_posted",
        {"verdict": "changes", "escalated": False},
    )

    assert state == "needs_work"


def test_a_pass_routes_to_the_human_as_before():
    state = event_transition(
        "reviewing", "reviewer_findings_posted", {"verdict": "pass"},
    )

    assert state == "awaiting_human"
