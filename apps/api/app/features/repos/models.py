from datetime import datetime

from pydantic import BaseModel


class RepoIn(BaseModel):
    slug: str
    name: str
    path: str


class Repo(BaseModel):
    id: int
    slug: str
    name: str
    path: str
    # Derived at read time from the checkout's README first paragraph — never stored.
    description: str | None = None
    created_at: datetime
