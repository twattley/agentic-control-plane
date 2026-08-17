from datetime import datetime

from pydantic import BaseModel


class RepoIn(BaseModel):
    slug: str
    name: str
    path: str
    # None = ungated. Registration may fill it with the repo's own documented
    # test command; it never invents one.
    close_gate_command: str | None = None


class RepoGateIn(BaseModel):
    """The one editable repo setting. Required-but-nullable: null clears the
    gate deliberately, an omitted field is a malformed request."""

    close_gate_command: str | None


class Repo(BaseModel):
    id: int
    slug: str
    name: str
    path: str
    close_gate_command: str | None = None
    # Derived at read time from the checkout's README first paragraph — never stored.
    description: str | None = None
    created_at: datetime
