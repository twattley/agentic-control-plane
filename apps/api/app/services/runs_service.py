"""Orchestrates run transitions across the state machine, events, leases,
artifacts, and decisions — each as one atomic transaction.

Controllers call these; repository holds SQL; state_machine decides legality.
Every state-changing operation computes the legal target state *before* writing,
so an illegal request touches no rows.
"""

import json

import asyncpg

from app.config import ROLE_FOR_STATE
from app.features.repos import repository as repos_repo
from app.features.runs import repository as repo
from app.features.runs.models import (
    Artifact,
    ArtifactIn,
    BoardPane,
    ClaimIn,
    DecisionIn,
    Event,
    EventIn,
    RevisionRequest,
    Run,
    RunDetail,
    RunIn,
    RunRevision,
)
from app.features.workflow import repository as workflow_repo
from app.services import executor, state_machine
from app.services.state_machine import IllegalTransitionError


class RunNotFoundError(Exception):
    def __init__(self, run_id: int):
        self.run_id = run_id
        super().__init__(f"run {run_id} not found")


class LeaseConflictError(Exception):
    """Role already actively leased on this run."""


class WorkUnitNotStartableError(Exception):
    """The portable workflow does not expose this identity as startable."""


async def _load(conn: asyncpg.Connection, run_id: int) -> Run:
    run = await repo.get_run(conn, run_id)
    if run is None:
        raise RunNotFoundError(run_id)
    return run


async def create_run(pool: asyncpg.Pool, data: RunIn) -> Run:
    repo_row = await repos_repo.get_repo(pool, data.repo_id)
    if repo_row is None:
        raise WorkUnitNotStartableError(f"repo {data.repo_id} not found")
    workflow = workflow_repo.load_workflow(repo_row.path)

    async with pool.acquire() as conn, conn.transaction():
        if workflow.ticket_contract == "epic-story-v1":
            story = next(
                (item for item in workflow.stories if item.story_id == data.ticket_id),
                None,
            )
            if (
                story is None
                or story.state != "ready"
                or "builder" not in story.claimable_roles
                or story.diagnostic_codes
            ):
                raise WorkUnitNotStartableError(
                    f"workflow identity {data.ticket_id!r} is not a startable story"
                )
            try:
                document = workflow_repo.document_from_workflow(
                    repo_row.path, workflow, data.ticket_id
                )
            except workflow_repo.WorkflowDocumentError as exc:
                raise WorkUnitNotStartableError(
                    f"workflow identity {data.ticket_id!r} has no safe unique document"
                ) from exc
            if document.kind != "story":
                raise WorkUnitNotStartableError(
                    f"workflow identity {data.ticket_id!r} is not a story document"
                )
            existing = await repo.list_runs(conn, data.repo_id)
            if any(
                run.ticket_id == data.ticket_id
                and run.state not in {"closed", "blocked"}
                for run in existing
            ):
                raise WorkUnitNotStartableError(
                    f"workflow identity {data.ticket_id!r} already has an active run"
                )
        run = await repo.create_run(conn, data)
        await repo.append_event(conn, run.id, EventIn(type="run_created", actor="system"))
    executor.maybe_dispatch(run, run.state)  # a new run is queued -> builder
    return run


async def list_runs(pool: asyncpg.Pool, repo_id: int | None = None) -> list[Run]:
    async with pool.acquire() as conn:
        return await repo.list_runs(conn, repo_id)


async def run_detail(pool: asyncpg.Pool, run_id: int) -> RunDetail:
    async with pool.acquire() as conn:
        run = await _load(conn, run_id)
        events = await repo.list_events(conn, run_id)
        artifacts = await repo.list_artifacts(conn, run_id)
        revisions, pending_request = _revision_history(events, artifacts)
        return RunDetail(
            run=run,
            events=events,
            artifacts=artifacts,
            leases=await repo.list_leases(conn, run_id),
            revisions=revisions,
            pending_revision_request=pending_request,
        )


def _revision_history(
    events: list[Event], artifacts: list[Artifact]
) -> tuple[list[RunRevision], RevisionRequest | None]:
    """Project append-only agent traffic into human-visible review turns."""
    artifact_by_id = {artifact.id: artifact for artifact in artifacts}
    first_base = _first_structured_base(events, artifact_by_id)
    legacy = _legacy_revision(
        events, artifact_by_id, before_event_id=first_base.id if first_base else None
    )
    revisions = [legacy] if legacy and first_base else []
    pending: RevisionRequest | None = None

    for event in events:
        if (
            event.type == "human_note_posted"
            and event.payload.get("decision") == "request_changes"
        ):
            pending = RevisionRequest(
                event_id=event.id,
                text=(event.payload.get("note") or "Changes requested").strip(),
                created_at=event.created_at,
            )
            continue

        checkpoint = event.payload.get("revision")
        if event.type != "reviewer_findings_posted" or not isinstance(checkpoint, dict):
            continue
        artifact_id = checkpoint.get("diff_artifact_id")
        artifact = artifact_by_id.get(artifact_id)
        brief = next(
            (prior for prior in reversed(events) if (
                prior.id < event.id and prior.type == "builder_brief_posted"
            )),
            None,
        )
        revisions.append(RunRevision(
            checkpoint_event_id=event.id,
            request_event_id=pending.event_id if pending else None,
            request=pending.text if pending else None,
            headline=_brief_headline(brief)
            if brief else str(checkpoint.get("headline") or "Work updated"),
            diff=artifact.content if artifact else "",
            created_at=event.created_at,
        ))
        pending = None

    if first_base or revisions:
        return revisions, pending

    # Runs created before revision checkpoints existed cannot yield trustworthy
    # increments. Preserve their useful current result without inventing history.
    return ([legacy] if legacy else []), pending


def _first_structured_base(
    events: list[Event], artifact_by_id: dict[int, Artifact]
) -> Event | None:
    for event in events:
        if event.type != "revision_base_attached":
            continue
        artifact = artifact_by_id.get(event.payload.get("artifact_id"))
        if artifact is None:
            continue
        try:
            snapshot = json.loads(artifact.content)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(snapshot, dict) and snapshot.get("tree"):
            return event
    return None


def _legacy_revision(
    events: list[Event], artifact_by_id: dict[int, Artifact],
    before_event_id: int | None = None,
) -> RunRevision | None:
    eligible = [
        event for event in events
        if before_event_id is None or event.id < before_event_id
    ]
    brief = next(
        (event for event in reversed(eligible) if event.type == "builder_brief_posted"),
        None,
    )
    diff_event = next(
        (event for event in reversed(eligible) if event.type == "diff_attached"),
        None,
    )
    diff = artifact_by_id.get(diff_event.payload.get("artifact_id")) if diff_event else None
    if brief is None and diff is None:
        return None
    source = brief or eligible[-1]
    return RunRevision(
        checkpoint_event_id=source.id,
        headline=_brief_headline(brief) if brief else "Work updated",
        diff=diff.content if diff else "",
        created_at=source.created_at,
    )


def _brief_headline(brief: Event) -> str:
    summary = str(brief.payload.get("summary") or "")
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    headline = brief.payload.get("headline") or (lines[0] if lines else "Work updated")
    return " ".join(str(headline).split())


async def claim(pool: asyncpg.Pool, run_id: int, data: ClaimIn) -> Run:
    async with pool.acquire() as conn, conn.transaction():
        run = await _load(conn, run_id)
        new_state = state_machine.claim_transition(run.state, data.role)  # may raise
        try:
            await repo.acquire_lease(conn, run_id, data.role, data.holder)
        except asyncpg.UniqueViolationError as exc:
            raise LeaseConflictError(f"{data.role} already leased on run {run_id}") from exc
        await repo.append_event(
            conn, run_id,
            EventIn(type=f"{data.role}_claimed", actor=data.role, payload={"holder": data.holder}),
        )
        await repo.set_state(conn, run_id, new_state)
        return (await repo.get_run(conn, run_id))  # type: ignore[return-value]


async def record_event(pool: asyncpg.Pool, run_id: int, data: EventIn) -> Event:
    async with pool.acquire() as conn, conn.transaction():
        run = await _load(conn, run_id)
        new_state = state_machine.event_transition(run.state, data.type, data.payload)  # may raise
        event = await repo.append_event(conn, run_id, data)
        if new_state is not None:
            # a state-moving event means the actor handed off — release their lease
            await repo.release_lease(conn, run_id, data.actor)
            await repo.set_state(conn, run_id, new_state)
    if new_state is not None:
        executor.maybe_dispatch(run, new_state)  # e.g. awaiting_review -> reviewer
    return event


async def attach_artifact(pool: asyncpg.Pool, run_id: int, data: ArtifactIn) -> Artifact:
    async with pool.acquire() as conn, conn.transaction():
        await _load(conn, run_id)
        artifact = await repo.add_artifact(conn, run_id, data)
        event_type = {
            "diff": "diff_attached",
            "revision_base": "revision_base_attached",
            "revision_diff": "revision_diff_attached",
        }.get(data.kind)
        if event_type:
            await repo.append_event(
                conn, run_id,
                EventIn(type=event_type, actor="builder",
                        payload={"artifact_id": artifact.id}),
            )
        return artifact


async def decide(pool: asyncpg.Pool, run_id: int, data: DecisionIn) -> Run:
    async with pool.acquire() as conn, conn.transaction():
        run = await _load(conn, run_id)
        new_state = state_machine.decision_transition(run.state, data.decision)  # may raise
        await repo.add_decision(conn, run_id, data.decision, data.note, data.actor)
        await repo.append_event(
            conn, run_id,
            EventIn(type=_DECISION_EVENT[data.decision], actor=data.actor,
                    payload={"note": data.note, "decision": data.decision}),
        )
        await repo.set_state(conn, run_id, new_state)
        updated = await repo.get_run(conn, run_id)
    executor.maybe_dispatch(updated, new_state)  # request_changes -> needs_work -> builder
    return updated  # type: ignore[return-value]


_DECISION_EVENT = {
    "approve": "human_approved",
    "request_changes": "human_note_posted",
    "block": "blocked",
    "close": "close_requested",  # closer worker then gates + commits -> closed
}


# Queue reads — the phone inbox. Each queue is "runs waiting on this actor".
_QUEUES = {
    "review": ["awaiting_review"],
    "fix": ["needs_work"],
    "human": ["awaiting_human"],
}


async def queue(pool: asyncpg.Pool, name: str) -> list[Run]:
    async with pool.acquire() as conn:
        return await repo.runs_in_states(conn, _QUEUES[name])


# Everything still moving — a pane per run in one of these.
_ACTIVE_STATES = [
    "queued", "building", "awaiting_review", "reviewing",
    "needs_work", "fixing", "awaiting_human", "approved", "closing",
]


async def board(pool: asyncpg.Pool) -> list[BoardPane]:
    """One pane per active run: run + repo name + frozen ticket summary + last
    event. The workbench reads this in a single request."""
    async with pool.acquire() as conn:
        runs = await repo.runs_in_states(conn, _ACTIVE_STATES)
        panes = []
        repos = {}
        workflows = {}
        for run in sorted(runs, key=lambda r: r.updated_at, reverse=True):
            if run.repo_id not in repos:
                repos[run.repo_id] = await repos_repo.get_repo(pool, run.repo_id)
            repo_row = repos[run.repo_id]
            if repo_row is None:
                continue
            if run.repo_id not in workflows:
                workflows[run.repo_id] = workflow_repo.load_workflow(repo_row.path)
            events = await repo.list_events(conn, run.id)
            try:
                document = workflow_repo.document_from_workflow(
                    repo_row.path, workflows[run.repo_id], run.ticket_id
                )
            except workflow_repo.WorkflowDocumentError:
                document = None
            panes.append(BoardPane(
                run=run,
                repo_name=repo_row.name,
                summary=document.summary if document else None,
                last_event=events[-1] if events else None,
            ))
        return panes


async def dispatch_current(pool: asyncpg.Pool, run_id: int, provider: str | None = None) -> str:
    """Manual re-run: force-dispatch the agent the current state is waiting on.
    An explicit `provider` overrides the run's stored choice for this pass only.

    Safe to press repeatedly — a duplicate worker loses the claim race and exits.
    """
    async with pool.acquire() as conn:
        run = await _load(conn, run_id)
    role = ROLE_FOR_STATE.get(run.state)
    if role is None:
        raise IllegalTransitionError(run.state, "dispatch")
    executor.dispatch(run_id, role, provider or executor.run_provider(run, role))
    return role
