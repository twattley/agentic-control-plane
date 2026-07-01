from datetime import datetime

from pydantic import BaseModel, Field


class RunIn(BaseModel):
    repo_id: int
    ticket_id: str
    title: str
    mode: str = "direct"  # 'direct' | 'tdd'


class Run(BaseModel):
    id: int
    repo_id: int
    ticket_id: str
    title: str
    mode: str
    state: str
    created_at: datetime
    updated_at: datetime


class ClaimIn(BaseModel):
    role: str          # builder | reviewer | human
    holder: str        # codex | claude | tom


class EventIn(BaseModel):
    type: str
    actor: str
    payload: dict = Field(default_factory=dict)


class Event(BaseModel):
    id: int
    run_id: int
    type: str
    actor: str
    payload: dict
    created_at: datetime


class ArtifactIn(BaseModel):
    kind: str          # diff | test_output | screenshot | log
    content: str


class Artifact(BaseModel):
    id: int
    run_id: int
    kind: str
    content: str
    created_at: datetime


class DecisionIn(BaseModel):
    decision: str      # approve | request_changes | block | close
    note: str | None = None
    actor: str = "human"


class Lease(BaseModel):
    id: int
    run_id: int
    role: str
    holder: str
    acquired_at: datetime
    released_at: datetime | None = None


class RunDetail(BaseModel):
    """Everything the phone needs to render a run in one payload."""

    run: Run
    events: list[Event]
    artifacts: list[Artifact]
    leases: list[Lease]
