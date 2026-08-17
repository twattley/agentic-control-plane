from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth import require_token
from app.database import get_pool
from app.features.discussions import repository
from app.features.discussions.models import (
    Discussion,
    DiscussionDetail,
    DiscussionStartIn,
    FreezeIn,
    MessageIn,
    SkillSummary,
)
from app.features.repos import repository as repos_repo
from app.features.repos.models import Repo
from app.features.tickets import repository as tickets_repo
from app.features.tickets.models import TicketDetail
from app.features.workflow import repository as workflow_repo
from app.features.workflow.models import StoryCreateIn
from app.services import discussion_agent
from app.services.discussion_agent import AgentError
from app.services.markdown import section

router = APIRouter(
    prefix="/api/v1/repos/{repo_id}/discussions",
    tags=["discussions"],
    dependencies=[Depends(require_token)],
)


async def _repo_or_404(repo_id: int) -> Repo:
    repo = await repos_repo.get_repo(await get_pool(), repo_id)
    if repo is None:
        raise HTTPException(status_code=404, detail=f"repo {repo_id} not found")
    return repo


async def _open_discussion_or_error(discussion_id: int, repo_id: int) -> Discussion:
    disc = await repository.get_discussion(await get_pool(), discussion_id)
    if disc is None or disc.repo_id != repo_id:
        raise HTTPException(status_code=404, detail=f"discussion {discussion_id} not found")
    if disc.state != "open":
        raise HTTPException(status_code=409, detail="discussion is frozen")
    return disc


async def _detail(discussion_id: int) -> DiscussionDetail:
    pool = await get_pool()
    disc = await repository.get_discussion(pool, discussion_id)
    return DiscussionDetail(
        discussion=disc,  # type: ignore[arg-type]
        messages=await repository.list_messages(pool, discussion_id),
    )


async def _turn(repo: Repo, disc: Discussion, message: str) -> DiscussionDetail:
    """One bounce: record the human message, run the agent in the checkout,
    record its reply. An agent failure records nothing."""
    pool = await get_pool()
    skill = _skill_or_422(repo, disc.skill_name)
    try:
        if skill is None:
            session_id, text = await discussion_agent.reply(
                repo.path, message, disc.session_id
            )
        else:
            session_id, text = await discussion_agent.reply(
                repo.path, message, disc.session_id, skill.prompt
            )
    except AgentError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from None
    await repository.add_message(pool, disc.id, "human", message)
    await repository.add_message(pool, disc.id, "agent", text)
    await repository.set_session(pool, disc.id, session_id)
    return await _detail(disc.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_discussion(repo_id: int, data: DiscussionStartIn) -> DiscussionDetail:
    repo = await _repo_or_404(repo_id)
    _skill_or_422(repo, data.skill_name)
    disc = await repository.create_discussion(
        await get_pool(), repo_id, data.skill_name
    )
    return await _turn(repo, disc, data.message)


@router.get("")
async def list_discussions(repo_id: int) -> list[Discussion]:
    await _repo_or_404(repo_id)
    return await repository.list_discussions(await get_pool(), repo_id)


@router.get("/skills")
async def list_skills(repo_id: int) -> list[SkillSummary]:
    repo = await _repo_or_404(repo_id)
    return [
        SkillSummary(name=skill.name, description=skill.description)
        for skill in discussion_agent.discover_skills(repo.path)
    ]


@router.get("/{discussion_id}")
async def get_discussion(repo_id: int, discussion_id: int) -> DiscussionDetail:
    await _repo_or_404(repo_id)
    disc = await repository.get_discussion(await get_pool(), discussion_id)
    if disc is None or disc.repo_id != repo_id:
        raise HTTPException(status_code=404, detail=f"discussion {discussion_id} not found")
    return await _detail(discussion_id)


@router.post("/{discussion_id}/messages")
async def send_message(repo_id: int, discussion_id: int, data: MessageIn) -> DiscussionDetail:
    repo = await _repo_or_404(repo_id)
    disc = await _open_discussion_or_error(discussion_id, repo_id)
    return await _turn(repo, disc, data.message)


@router.post("/{discussion_id}/freeze")
async def freeze_discussion(repo_id: int, discussion_id: int, data: FreezeIn) -> TicketDetail:
    """The freeze step: one final agent turn produces the ticket markdown, and
    the PLANE writes the file — the agent never does. Legacy repos get a flat
    ticket at `slug`; contract repos get a story under `epic_id` or a
    standalone story, with identity allocated by the repo's own create-story
    tool."""
    if data.slug is None and data.epic_id is None and not data.standalone:
        raise HTTPException(
            status_code=422, detail="freeze needs a slug, an epic_id, or standalone"
        )
    if data.epic_id is not None and data.standalone:
        raise HTTPException(
            status_code=422, detail="freeze takes an epic_id or standalone, not both"
        )
    repo = await _repo_or_404(repo_id)
    disc = await _open_discussion_or_error(discussion_id, repo_id)
    detail = await _turn(repo, disc, discussion_agent.FREEZE_PROMPT)
    content = discussion_agent.note_skill(
        discussion_agent.strip_fence(detail.messages[-1].content),
        disc.skill_name,
    )
    _require_freeze_contract(content)

    if data.epic_id is not None or data.standalone:
        ticket = _freeze_story(repo, data, content)
    else:
        try:
            ticket = tickets_repo.create_ticket(repo.path, data.slug, content)
        except tickets_repo.TicketExistsError:
            raise HTTPException(
                status_code=409, detail=f"ticket {data.slug} already exists"
            ) from None
    await repository.set_frozen(await get_pool(), discussion_id, ticket.slug)
    return ticket


def _require_freeze_contract(content: str) -> None:
    scope = section(content, "Scope")
    missing = []
    if scope is None or not _has_allowed_paths(scope):
        missing.append("Scope/allowed_paths")
    if section(content, "Validation") is None:
        missing.append("Validation")
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"frozen ticket is missing required contract sections: {', '.join(missing)}",
        )


def _has_allowed_paths(scope: str) -> bool:
    """The allowed_paths field must contain at least one nested list item."""
    lines = scope.splitlines()
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        field = stripped.removeprefix("-").strip().removesuffix(":").strip("` ")
        if not stripped.endswith(":") or field != "allowed_paths":
            continue

        field_indent = len(raw) - len(raw.lstrip())
        for candidate in lines[index + 1:]:
            if not candidate.strip():
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= field_indent:
                return False
            if candidate.strip().startswith("-") and candidate.strip()[1:].strip("` "):
                return True
        return False
    return False


def _skill_or_422(
    repo: Repo, skill_name: str | None
) -> discussion_agent.SkillDefinition | None:
    try:
        return discussion_agent.resolve_skill(repo.path, skill_name)
    except discussion_agent.SkillUnavailableError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None


def _freeze_story(repo: Repo, data: FreezeIn, content: str) -> TicketDetail:
    title, body = _split_title(content)
    try:
        authored = workflow_repo.create_story(repo.path, StoryCreateIn(
            epic_id=data.epic_id, coordination_class=data.coordination_class,
            title=title, body=body,
        ))
    except workflow_repo.WorkflowAuthorError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except workflow_repo.WorkflowReadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    path = Path(repo.path) / authored.path
    return TicketDetail(
        slug=authored.story_id, title=authored.title,
        summary=tickets_repo.ticket_summary(path), content=path.read_text(),
    )


def _split_title(content: str) -> tuple[str, str]:
    """First `# ` heading becomes the story title; the rest is the body."""
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip(), "\n".join(lines[i + 1:]).strip()
    return "Shaped story", content.strip()
