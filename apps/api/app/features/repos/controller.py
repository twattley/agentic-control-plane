from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_token
from app.config import settings
from app.database import get_pool
from app.features.repos import repository
from app.features.repos.models import AvailableProject, Repo, RepoIn

router = APIRouter(prefix="/api/v1/repos", tags=["repos"], dependencies=[Depends(require_token)])


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_repo(data: RepoIn) -> Repo:
    return await repository.upsert_repo(await get_pool(), data)


@router.get("")
async def list_repos() -> list[Repo]:
    return await repository.list_repos(await get_pool())


@router.get("/available")
async def available_projects() -> list[AvailableProject]:
    """Directories under the configured projects root — the register dropdown."""
    root = Path(settings.projects_root)
    if not root.is_dir():
        return []
    return [
        AvailableProject(name=p.name, path=str(p), is_git=(p / ".git").is_dir())
        for p in sorted(root.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]


@router.get("/{repo_id}")
async def get_repo(repo_id: int) -> Repo:
    repo = await repository.get_repo(await get_pool(), repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"repo {repo_id} not found")
    return repo
