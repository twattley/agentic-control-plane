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
    created_at: datetime


class AvailableProject(BaseModel):
    """A directory under the projects root that could be registered."""

    name: str
    path: str
    is_git: bool
