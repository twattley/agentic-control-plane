from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CoordinationClass = Literal["contract", "platform", "feature", "validation"]


class SnapshotRecord(BaseModel):
    model_config = ConfigDict(extra="allow", strict=True)


class WorkflowEpic(SnapshotRecord):
    kind: Literal["epic"]
    epic_id: str
    title: str
    path: str
    story_ids: list[str]
    story_counts: dict[str, int]


class WorkflowStory(SnapshotRecord):
    kind: Literal["story"]
    story_id: str
    epic_id: str
    coordination_class: str
    state: str
    title: str
    path: str
    claimable_roles: list[str]
    diagnostic_codes: list[str]


class WorkflowLegacy(SnapshotRecord):
    kind: Literal["legacy"]
    legacy_id: str
    title: str
    path: str
    state: str | None = None


class WorkflowRun(SnapshotRecord):
    id: str
    project_slug: str
    work_unit_id: str
    ticket_path: str
    agent: str
    role: str
    status: str
    independent_review: bool | None = None
    git_ref: str | None = None
    claimed_at: str | None = None
    completed_at: str | None = None
    abandoned_at: str | None = None
    last_event: str | None = None
    last_event_at: str | None = None
    ticket_kind: Literal["story", "legacy"] | None = None


class WorkflowDiagnostic(SnapshotRecord):
    source: str
    code: str
    message: str
    path: str
    related_paths: list[str]


class WorkflowSnapshot(BaseModel):
    model_config = ConfigDict(strict=True)

    schema_version: Literal["agent-workflow-snapshot-v1"]
    ticket_contract: Literal["epic-story-v1"] | None
    epics: list[WorkflowEpic]
    stories: list[WorkflowStory]
    legacy: list[WorkflowLegacy]
    runs: list[WorkflowRun]
    diagnostics: list[WorkflowDiagnostic]


class WorkflowProjection(WorkflowSnapshot):
    source: Literal["agent-workflow-snapshot-v1", "legacy-flat"]
    schema_version: Literal["agent-workflow-snapshot-v1"] | None


class WorkflowDocument(BaseModel):
    identity: str
    kind: Literal["epic", "story", "legacy"]
    path: str
    title: str
    summary: str | None
    content: str


class StoryCreateIn(BaseModel):
    """Author a story through the repo's own create-story tool; the optional
    body (from a freeze or the composer) replaces the skeleton's sections."""

    epic_id: str
    coordination_class: CoordinationClass
    title: str = Field(min_length=1)
    body: str | None = None


class AdoptIn(BaseModel):
    """The contract's explicit legacy migration: a human names the legacy
    ticket and the epic it belongs under; the tool allocates the identity."""

    legacy_id: str
    epic_id: str
    coordination_class: CoordinationClass


class AuthoredStory(BaseModel):
    story_id: str
    epic_id: str
    coordination_class: str
    state: str
    title: str
    path: str
