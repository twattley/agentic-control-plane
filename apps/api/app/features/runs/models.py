from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Mirrored by ArtifactKind in packages/domain-types. `evidence` is optional
# markdown a builder leaves to demonstrate the outcome.
ArtifactKind = Literal["diff", "test_output", "screenshot", "log", "evidence"]


class RunIn(BaseModel):
    repo_id: int
    ticket_id: str
    title: str
    mode: str = "direct"  # 'direct' | 'tdd'
    # Agent choice per role, as "provider[:model]" — e.g. "claude:sonnet",
    # "codex". None falls back to the global settings default.
    builder_provider: str | None = None
    reviewer_provider: str | None = None


class Run(BaseModel):
    id: int
    repo_id: int
    ticket_id: str
    title: str
    mode: str
    state: str
    builder_provider: str | None = None
    reviewer_provider: str | None = None
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
    kind: ArtifactKind
    content: str


class Artifact(BaseModel):
    id: int
    run_id: int
    kind: ArtifactKind
    content: str
    created_at: datetime


class DispatchIn(BaseModel):
    """One-off override for a manual dispatch; omit to use the run's choice."""

    provider: str | None = None  # "provider[:model]"


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


class BoardPane(BaseModel):
    """One workbench pane: an active run plus everything needed to re-enter it
    cold — project name, the frozen ticket summary, and what just happened."""

    run: Run
    repo_name: str
    summary: str | None
    last_event: Event | None
