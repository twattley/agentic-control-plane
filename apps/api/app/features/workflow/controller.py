from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_token
from app.database import get_pool
from app.features.repos import repository as repos_repo
from app.features.repos.models import Repo
from app.features.workflow import repository
from app.features.workflow.models import (
    AdoptIn,
    AuthoredStory,
    CompactIn,
    CompactResult,
    StoryCreateIn,
    WorkflowDocument,
    WorkflowProjection,
)

router = APIRouter(
    prefix="/api/v1/repos/{repo_id}/workflow",
    tags=["workflow"],
    dependencies=[Depends(require_token)],
)


async def _repo_or_404(repo_id: int) -> Repo:
    repo = await repos_repo.get_repo(await get_pool(), repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"repo {repo_id} not found")
    return repo


@router.get("")
async def get_workflow(repo_id: int) -> WorkflowProjection:
    repo = await _repo_or_404(repo_id)
    try:
        return repository.load_workflow(repo.path)
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/document")
async def get_workflow_document_by_path(repo_id: int, path: str) -> WorkflowDocument:
    """Read a work document by its current path — the only way to name one of
    several nested legacy files that share a filename stem."""
    repo = await _repo_or_404(repo_id)
    try:
        return repository.get_document_by_path(repo.path, path)
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except repository.WorkflowDocumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/documents/{identity}")
async def get_workflow_document(repo_id: int, identity: str) -> WorkflowDocument:
    repo = await _repo_or_404(repo_id)
    try:
        return repository.get_document(repo.path, identity)
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except repository.WorkflowDocumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/stories", status_code=status.HTTP_201_CREATED)
async def create_story(repo_id: int, data: StoryCreateIn) -> AuthoredStory:
    repo = await _repo_or_404(repo_id)
    try:
        return repository.create_story(repo.path, data)
    except repository.WorkflowAuthorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stories/adopt", status_code=status.HTTP_201_CREATED)
async def adopt_legacy(repo_id: int, data: AdoptIn) -> AuthoredStory:
    repo = await _repo_or_404(repo_id)
    try:
        return repository.adopt_legacy(
            repo.path, data.legacy_id, data.epic_id, data.coordination_class
        )
    except repository.WorkflowDocumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except repository.WorkflowAuthorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/compact")
async def compact(repo_id: int, data: CompactIn) -> CompactResult:
    repo = await _repo_or_404(repo_id)
    try:
        return repository.compact(repo.path, data)
    except repository.WorkflowAuthorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stories/{story_id}/ready")
async def mark_story_ready(repo_id: int, story_id: str) -> AuthoredStory:
    repo = await _repo_or_404(repo_id)
    try:
        return repository.mark_ready(repo.path, story_id)
    except repository.WorkflowDocumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except repository.WorkflowAuthorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
