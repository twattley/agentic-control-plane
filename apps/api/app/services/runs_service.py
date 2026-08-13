"""Orchestrates run transitions across the state machine, events, leases,
artifacts, and decisions — each as one atomic transaction.

Controllers call these; repository holds SQL; state_machine decides legality.
Every state-changing operation computes the legal target state *before* writing,
so an illegal request touches no rows.
"""

from pathlib import Path

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
    Run,
    RunDetail,
    RunIn,
)
from app.features.tickets.repository import ticket_summary
from app.services import executor, state_machine
from app.services.state_machine import IllegalTransitionError


class RunNotFoundError(Exception):
    def __init__(self, run_id: int):
        self.run_id = run_id
        super().__init__(f"run {run_id} not found")


class LeaseConflictError(Exception):
    """Role already actively leased on this run."""


async def _load(conn: asyncpg.Connection, run_id: int) -> Run:
    run = await repo.get_run(conn, run_id)
    if run is None:
        raise RunNotFoundError(run_id)
    return run


async def create_run(pool: asyncpg.Pool, data: RunIn) -> Run:
    async with pool.acquire() as conn, conn.transaction():
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
        return RunDetail(
            run=run,
            events=await repo.list_events(conn, run_id),
            artifacts=await repo.list_artifacts(conn, run_id),
            leases=await repo.list_leases(conn, run_id),
        )


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
        if data.kind == "diff":
            await repo.append_event(
                conn, run_id,
                EventIn(type="diff_attached", actor="builder",
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
                    payload={"note": data.note}),
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
        for run in sorted(runs, key=lambda r: r.updated_at, reverse=True):
            repo_row = await repos_repo.get_repo(pool, run.repo_id)
            if repo_row is None:
                continue
            events = await repo.list_events(conn, run.id)
            ticket_file = Path(repo_row.path) / "tickets" / f"{run.ticket_id}.md"
            panes.append(BoardPane(
                run=run,
                repo_name=repo_row.name,
                summary=ticket_summary(ticket_file) if ticket_file.is_file() else None,
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
