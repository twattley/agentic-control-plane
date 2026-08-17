from datetime import datetime

from pydantic import BaseModel, Field

SLUG_PATTERN = r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$"  # filename stem, never a path


class DiscussionStartIn(BaseModel):
    message: str = Field(min_length=1)
    skill_name: str | None = None


class SkillSummary(BaseModel):
    name: str
    description: str


class MessageIn(BaseModel):
    message: str = Field(min_length=1)


class FreezeIn(BaseModel):
    """Legacy repos freeze to a flat slug; contract repos freeze into a story
    under an epic, or standalone when the repo has no epic to hang it on (the
    plane delegates identity to the repo's own tool either way)."""

    slug: str | None = Field(default=None, pattern=SLUG_PATTERN)
    epic_id: str | None = None
    standalone: bool = False
    coordination_class: str = "feature"


class Discussion(BaseModel):
    id: int
    repo_id: int
    session_id: str | None
    state: str          # open | frozen
    ticket_slug: str | None
    skill_name: str | None
    created_at: datetime
    updated_at: datetime


class DiscussionMessage(BaseModel):
    id: int
    discussion_id: int
    role: str           # human | agent
    content: str
    created_at: datetime


class DiscussionDetail(BaseModel):
    discussion: Discussion
    messages: list[DiscussionMessage]
