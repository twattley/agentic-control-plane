import json

from app.worker import _capped_verdict, _parse_verdict


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


def test_cap_flips_changes_to_pass_after_limit():
    assert _capped_verdict("changes", prior_changes=2, cap=2) == "pass"
    assert _capped_verdict("changes", prior_changes=1, cap=2) == "changes"
    assert _capped_verdict("pass", prior_changes=5, cap=2) == "pass"
