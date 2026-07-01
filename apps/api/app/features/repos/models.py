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
