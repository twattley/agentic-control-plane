from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_token
from app.database import get_pool
from app.features.repos import repository as repos_repo
from app.features.repos.models import Repo
from app.features.tickets import repository
from app.features.tickets.models import Ticket, TicketDetail

router = APIRouter(
    prefix="/api/v1/repos/{repo_id}/tickets",
    tags=["tickets"],
    dependencies=[Depends(require_token)],
)


async def _repo_or_404(repo_id: int) -> Repo:
    repo = await repos_repo.get_repo(await get_pool(), repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"repo {repo_id} not found")
    return repo


@router.get("")
async def list_tickets(repo_id: int) -> list[Ticket]:
    repo = await _repo_or_404(repo_id)
    return repository.list_tickets(repo.path)


@router.get("/{slug}")
async def get_ticket(repo_id: int, slug: str) -> TicketDetail:
    repo = await _repo_or_404(repo_id)
    ticket = repository.get_ticket(repo.path, slug)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {slug} not found")
    return ticket
