from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_token
from app.config import settings
from app.database import get_pool
from app.features.repos import repository
from app.features.repos.models import Repo, RepoIn
from app.services.markdown import first_prose_paragraph

router = APIRouter(prefix="/api/v1/repos", tags=["repos"], dependencies=[Depends(require_token)])


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_repo(data: RepoIn) -> Repo:
    return await repository.upsert_repo(await get_pool(), data)


@router.get("")
async def list_repos() -> list[Repo]:
    """The projects list IS the projects folder: scan it, register any new git
    repo, and show only repos that still exist under the root. Rows whose path
    moved away are hidden, never deleted — their run history must survive.
    A `.planeignore` file at a checkout's root opts that project out."""
    pool = await get_pool()
    root = Path(settings.projects_root)
    await repository.sync_repos(pool, _scan(root))
    return [
        _described(r) for r in await repository.list_repos(pool)
        if Path(r.path).parent == root and _visible(Path(r.path))
    ]


def _scan(root: Path) -> list[RepoIn]:
    if not root.is_dir():
        return []
    return [
        RepoIn(slug=p.name, name=_pretty(p.name), path=str(p))
        for p in sorted(root.iterdir())
        if p.is_dir() and not p.name.startswith(".") and (p / ".git").is_dir() and _visible(p)
    ]


def _visible(path: Path) -> bool:
    return path.is_dir() and not (path / ".planeignore").exists()


def _pretty(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.replace("_", "-").split("-") if w)


def _described(repo: Repo) -> Repo:
    readme = Path(repo.path) / "README.md"
    repo.description = first_prose_paragraph(readme.read_text()) if readme.is_file() else None
    return repo


@router.get("/{repo_id}")
async def get_repo(repo_id: int) -> Repo:
    repo = await repository.get_repo(await get_pool(), repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"repo {repo_id} not found")
    return _described(repo)
