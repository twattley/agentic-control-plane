from datetime import datetime

from pydantic import BaseModel, Field

SLUG_PATTERN = r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$"  # filename stem, never a path


class DiscussionStartIn(BaseModel):
    message: str = Field(min_length=1)


class MessageIn(BaseModel):
    message: str = Field(min_length=1)


class FreezeIn(BaseModel):
    slug: str = Field(pattern=SLUG_PATTERN)


class Discussion(BaseModel):
    id: int
    repo_id: int
    session_id: str | None
    state: str          # open | frozen
    ticket_slug: str | None
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
