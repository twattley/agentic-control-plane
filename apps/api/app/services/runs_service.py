"""Orchestrates run transitions across the state machine, events, leases,
artifacts, and decisions — each as one atomic transaction.

Controllers call these; repository holds SQL; state_machine decides legality.
Every state-changing operation computes the legal target state *before* writing,
so an illegal request touches no rows.
"""

import asyncpg

from app.features.runs import repository as repo
from app.features.runs.models import (
    Artifact,
    ArtifactIn,
    ClaimIn,
    DecisionIn,
    Event,
    EventIn,
    Run,
    RunDetail,
    RunIn,
)
from app.services import state_machine


class RunNotFound(Exception):
    def __init__(self, run_id: int):
        self.run_id = run_id
        super().__init__(f"run {run_id} not found")


class LeaseConflict(Exception):
    """Role already actively leased on this run."""


async def _load(conn: asyncpg.Connection, run_id: int) -> Run:
    run = await repo.get_run(conn, run_id)
    if run is None:
        raise RunNotFound(run_id)
    return run


async def create_run(pool: asyncpg.Pool, data: RunIn) -> Run:
    async with pool.acquire() as conn, conn.transaction():
        run = await repo.create_run(conn, data)
        await repo.append_event(conn, run.id, EventIn(type="run_created", actor="system"))
        return run


async def list_runs(pool: asyncpg.Pool) -> list[Run]:
    async with pool.acquire() as conn:
        return await repo.list_runs(conn)


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
        new_state = state_machine.claim_transition(run.state, data.role)  # may raise IllegalTransition
        try:
            await repo.acquire_lease(conn, run_id, data.role, data.holder)
        except asyncpg.UniqueViolationError as exc:
            raise LeaseConflict(f"{data.role} already leased on run {run_id}") from exc
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
        return event


async def attach_artifact(pool: asyncpg.Pool, run_id: int, data: ArtifactIn) -> Artifact:
    async with pool.acquire() as conn, conn.transaction():
        await _load(conn, run_id)
        artifact = await repo.add_artifact(conn, run_id, data)
        if data.kind == "diff":
            await repo.append_event(
                conn, run_id,
                EventIn(type="diff_attached", actor="builder", payload={"artifact_id": artifact.id}),
            )
        return artifact


async def decide(pool: asyncpg.Pool, run_id: int, data: DecisionIn) -> Run:
    async with pool.acquire() as conn, conn.transaction():
        run = await _load(conn, run_id)
        new_state = state_machine.decision_transition(run.state, data.decision)  # may raise
        await repo.add_decision(conn, run_id, data.decision, data.note, data.actor)
        await repo.append_event(
            conn, run_id,
            EventIn(type=_DECISION_EVENT[data.decision], actor=data.actor, payload={"note": data.note}),
        )
        await repo.set_state(conn, run_id, new_state)
        return (await repo.get_run(conn, run_id))  # type: ignore[return-value]


_DECISION_EVENT = {
    "approve": "human_approved",
    "request_changes": "human_note_posted",
    "block": "blocked",
    "close": "closed",
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
