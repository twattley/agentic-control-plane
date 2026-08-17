"""Runs-feature fixtures.

acp-034: dispatched passes read each role's method from the installed skill
layer. Tests must never depend on the host's real ~/.claude/skills, so every
test in this package gets a temp skill dir with stub ROLE.md files; tests
that need a missing or custom method overwrite the seam themselves.
"""

import pytest

from app import worker

STUB_BUILDER_METHOD = "STUB BUILDER METHOD: build inside the boundary."
STUB_REVIEWER_METHOD = "STUB REVIEWER METHOD: locate every finding."


@pytest.fixture(autouse=True)
def role_methods(tmp_path_factory, monkeypatch):
    skills = tmp_path_factory.mktemp("skills")
    for role, text in (
        ("builder", STUB_BUILDER_METHOD),
        ("reviewer", STUB_REVIEWER_METHOD),
    ):
        role_dir = skills / role
        role_dir.mkdir()
        (role_dir / "ROLE.md").write_text(text + "\n")
    monkeypatch.setattr(worker, "_SKILLS_DIR", skills)
    return skills
