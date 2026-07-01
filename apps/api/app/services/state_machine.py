"""The builder/reviewer workflow state machine.

Pure logic, no I/O. The control plane's whole value is that run state can only
move along legal edges — this module is the single authority on what those are.
Callers apply a transition, catch `IllegalTransitionError`, and map it to HTTP 409.
"""

from __future__ import annotations

STATES = frozenset({
    "queued", "building", "awaiting_review", "reviewing",
    "needs_work", "fixing", "awaiting_human", "approved",
    "closed", "blocked",
})

# States a run can still be actively worked from (block is always legal here).
_ACTIVE = STATES - {"approved", "closed", "blocked"}


class IllegalTransitionError(Exception):
    """Raised when a requested transition is not a legal edge."""

    def __init__(self, frm: str, trigger: str):
        self.frm = frm
        self.trigger = trigger
        super().__init__(f"illegal transition from '{frm}' via '{trigger}'")


# role -> {from_state: to_state} for POST /runs/:id/claim
_CLAIM: dict[str, dict[str, str]] = {
    "builder": {"queued": "building", "needs_work": "fixing"},
    "reviewer": {"awaiting_review": "reviewing"},
}

# event type -> {from_state: to_state} for POST /runs/:id/events.
# Event types absent here are informational and never move state.
_EVENT: dict[str, dict[str, str]] = {
    "builder_brief_posted": {"building": "awaiting_review", "fixing": "awaiting_review"},
    # reviewer verdict splits by payload; handled in event_transition below.
}

# decision -> {from_state: to_state} for POST /runs/:id/decision
_DECISION: dict[str, dict[str, str]] = {
    "approve": {"awaiting_human": "approved"},
    "request_changes": {"awaiting_human": "needs_work"},
    "close": {"approved": "closed"},
    # block is special-cased: legal from any active state.
}


def claim_transition(state: str, role: str) -> str:
    """New state after `role` claims a run in `state`."""
    to = _CLAIM.get(role, {}).get(state)
    if to is None:
        raise IllegalTransitionError(state, f"claim:{role}")
    return to


def event_transition(state: str, event_type: str, payload: dict | None = None) -> str | None:
    """New state after an event, or None when the event doesn't move state.

    A reviewer's findings split on `payload['verdict']`: 'pass' sends the run to
    the human, anything else (changes requested) sends it back to the builder.
    """
    if event_type == "reviewer_findings_posted":
        if state != "reviewing":
            raise IllegalTransitionError(state, event_type)
        verdict = (payload or {}).get("verdict")
        return "awaiting_human" if verdict == "pass" else "needs_work"

    edges = _EVENT.get(event_type)
    if edges is None:
        return None  # informational event (reply, note); allowed, no move
    to = edges.get(state)
    if to is None:
        raise IllegalTransitionError(state, event_type)
    return to


def decision_transition(state: str, decision: str) -> str:
    """New state after a human decision."""
    if decision == "block":
        if state not in _ACTIVE:
            raise IllegalTransitionError(state, "block")
        return "blocked"
    to = _DECISION.get(decision, {}).get(state)
    if to is None:
        raise IllegalTransitionError(state, f"decision:{decision}")
    return to
