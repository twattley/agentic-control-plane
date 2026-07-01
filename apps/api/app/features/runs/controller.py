from enum import StrEnum

from fastapi import APIRouter, Depends, status

from app.auth import require_token
from app.database import get_pool
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
from app.services import runs_service

router = APIRouter(prefix="/api/v1", tags=["runs"], dependencies=[Depends(require_token)])


class QueueName(StrEnum):
    review = "review"
    fix = "fix"
    human = "human"


@router.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_run(data: RunIn) -> Run:
    return await runs_service.create_run(await get_pool(), data)


@router.get("/runs")
async def list_runs(repo_id: int | None = None) -> list[Run]:
    return await runs_service.list_runs(await get_pool(), repo_id)


@router.get("/runs/{run_id}")
async def get_run(run_id: int) -> RunDetail:
    return await runs_service.run_detail(await get_pool(), run_id)


@router.post("/runs/{run_id}/claim")
async def claim_run(run_id: int, data: ClaimIn) -> Run:
    return await runs_service.claim(await get_pool(), run_id, data)


@router.post("/runs/{run_id}/events", status_code=status.HTTP_201_CREATED)
async def post_event(run_id: int, data: EventIn) -> Event:
    return await runs_service.record_event(await get_pool(), run_id, data)


@router.post("/runs/{run_id}/artifacts", status_code=status.HTTP_201_CREATED)
async def post_artifact(run_id: int, data: ArtifactIn) -> Artifact:
    return await runs_service.attach_artifact(await get_pool(), run_id, data)


@router.post("/runs/{run_id}/decision")
async def post_decision(run_id: int, data: DecisionIn) -> Run:
    return await runs_service.decide(await get_pool(), run_id, data)


@router.post("/runs/{run_id}/dispatch", status_code=status.HTTP_202_ACCEPTED)
async def dispatch_run(run_id: int) -> dict:
    """Manual re-run: (re)dispatch the agent the current state is waiting on."""
    role = await runs_service.dispatch_current(await get_pool(), run_id)
    return {"dispatched": role}


@router.get("/queue/{name}")
async def get_queue(name: QueueName) -> list[Run]:
    return await runs_service.queue(await get_pool(), name.value)
