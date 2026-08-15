from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_token
from app.database import get_pool
from app.features.repos import repository as repos_repo
from app.features.repos.models import Repo
from app.features.workflow import repository
from app.features.workflow.models import WorkflowDocument, WorkflowProjection

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


@router.get("/documents/{identity}")
async def get_workflow_document(repo_id: int, identity: str) -> WorkflowDocument:
    repo = await _repo_or_404(repo_id)
    try:
        return repository.get_document(repo.path, identity)
    except repository.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except repository.WorkflowDocumentError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
