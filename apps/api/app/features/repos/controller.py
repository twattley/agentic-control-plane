import json
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_token
from app.config import settings
from app.database import get_pool
from app.features.repos import repository
from app.features.repos.models import Repo, RepoGateIn, RepoIn
from app.services.markdown import first_prose_paragraph

router = APIRouter(prefix="/api/v1/repos", tags=["repos"], dependencies=[Depends(require_token)])


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_repo(data: RepoIn) -> Repo:
    # Blank -> no gate specified. Filling the blank from the repo's own docs is
    # suggestion, not invention; finding nothing leaves the repo visibly ungated.
    gate = (data.close_gate_command or "").strip() or _documented_test_command(Path(data.path))
    registration = data.model_copy(update={"close_gate_command": gate})
    return await repository.upsert_repo(await get_pool(), registration)


def _documented_test_command(path: Path) -> str | None:
    """The test command the repo itself documents, or None — never a guess.
    Only conventions whose presence IS the documentation qualify: a Makefile
    `test` target, an npm `test` script."""
    makefile = path / "Makefile"
    if makefile.is_file() and re.search(r"^test\s*:", makefile.read_text(), re.M):
        return "make test"
    package = path / "package.json"
    if package.is_file():
        try:
            scripts = json.loads(package.read_text()).get("scripts", {})
        except (json.JSONDecodeError, AttributeError):
            scripts = {}
        if "test" in scripts:
            return "npm test"
    return None


@router.put("/{repo_id}/gate")
async def set_close_gate(repo_id: int, data: RepoGateIn) -> Repo:
    # A whitespace command would run `bash -lc ""` — exit 0, a gate that checks
    # nothing while looking configured. Normalise it to honestly ungated.
    command = (data.close_gate_command or "").strip() or None
    repo = await repository.set_close_gate(await get_pool(), repo_id, command)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"repo {repo_id} not found")
    return _described(repo)


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
        RepoIn(slug=p.name, name=_pretty(p.name), path=str(p),
               close_gate_command=_documented_test_command(p))
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
