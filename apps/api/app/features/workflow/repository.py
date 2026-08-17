import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import get_args

from pydantic import ValidationError

from app.features.tickets.repository import list_tickets, ticket_summary
from app.features.workflow.models import (
    AuthoredStory,
    SchemaVersion,
    StoryCreateIn,
    WorkflowDocument,
    WorkflowLegacy,
    WorkflowProjection,
    WorkflowSnapshot,
)

# Both are read so the portable tool can flip its emitter without taking
# every project page down while consumers catch up.
_SCHEMA_VERSIONS = get_args(SchemaVersion)
_TIMEOUT_SECONDS = 5


class WorkflowReadError(Exception):
    """A present adapter failed to provide the exact supported snapshot."""


class WorkflowDocumentError(Exception):
    """A stable identity did not resolve to one safe current document."""


class WorkflowAuthorError(Exception):
    """Story authoring refused: no tool, or the story is in the wrong state."""


def load_workflow(repo_path: str) -> WorkflowProjection:
    root = Path(repo_path).resolve()
    command = root / "scripts" / "agent_workflow"
    if not command.is_file():
        return _legacy_projection(root)

    try:
        result = subprocess.run(
            [str(command), "snapshot"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    # UnicodeDecodeError is a ValueError, not an OSError: `text=True` decodes
    # strictly, so an adapter emitting non-UTF-8 bytes escaped as an unhandled
    # 500 instead of the 502 every other adapter failure returns.
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        raise WorkflowReadError(f"workflow snapshot command failed: {exc}") from exc

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise WorkflowReadError("workflow snapshot emitted invalid JSON") from exc
    if not isinstance(raw, dict):
        raise WorkflowReadError("workflow snapshot must be a JSON object")
    if raw.get("schema_version") not in _SCHEMA_VERSIONS:
        raise WorkflowReadError(
            f"unsupported workflow schema: {raw.get('schema_version')!r}"
        )

    try:
        snapshot = WorkflowSnapshot.model_validate(raw)
    except ValidationError as exc:
        raise WorkflowReadError(f"invalid workflow snapshot: {exc}") from exc
    return WorkflowProjection(
        source=snapshot.schema_version,
        **snapshot.model_dump(),
    )


def get_document_by_path(repo_path: str, locator: str) -> WorkflowDocument:
    """Read one work document by its current path. Nested legacy files can share
    a filename stem, so a path — not an identity — is what reliably names a file
    on screen. Identity stays the run-level concept."""
    root = Path(repo_path).resolve()
    path = _safe_ticket_path(root, locator)
    workflow = load_workflow(repo_path)

    for item in workflow.stories:
        if item.path == locator:
            return _document(item.story_id, "story", locator, item.title, path)
    for item in workflow.epics:
        if item.path == locator:
            return _document(item.epic_id, "epic", locator, item.title, path)
    for item in workflow.legacy:
        if item.path == locator:
            return _document(item.legacy_id, "legacy", locator, item.title, path)
    raise WorkflowDocumentError(f"{locator!r} is not in this repo's workflow")


def _document(
    identity: str, kind: str, locator: str, title: str, path: Path
) -> WorkflowDocument:
    return WorkflowDocument(
        identity=identity, kind=kind, path=locator, title=title,  # type: ignore[arg-type]
        summary=ticket_summary(path), content=path.read_text(),
    )


def get_document(repo_path: str, identity: str) -> WorkflowDocument:
    workflow = load_workflow(repo_path)
    return document_from_workflow(repo_path, workflow, identity)


def document_from_workflow(
    repo_path: str, workflow: WorkflowProjection, identity: str
) -> WorkflowDocument:
    root = Path(repo_path).resolve()
    matches: list[tuple[str, str, str, str]] = []
    matches.extend(
        ("epic", item.epic_id, item.path, item.title)
        for item in workflow.epics if item.epic_id == identity
    )
    matches.extend(
        ("story", item.story_id, item.path, item.title)
        for item in workflow.stories if item.story_id == identity
    )
    matches.extend(
        ("legacy", item.legacy_id, item.path, item.title)
        for item in workflow.legacy if item.legacy_id == identity
    )
    if len(matches) != 1:
        raise WorkflowDocumentError(f"workflow identity {identity!r} is not unique")

    kind, stable_id, locator, title = matches[0]
    path = _safe_ticket_path(root, locator)
    content = path.read_text()
    return WorkflowDocument(
        identity=stable_id,
        kind=kind,
        path=locator,
        title=title,
        summary=ticket_summary(path),
        content=content,
    )


def create_story(repo_path: str, data: StoryCreateIn) -> AuthoredStory:
    """Delegate identity allocation and skeleton authoring to the repo's own
    tool, then merge the shaped body (if any) below the skeleton's Status."""
    root = Path(repo_path).resolve()
    command = root / "scripts" / "agent_workflow"
    if not command.is_file():
        raise WorkflowAuthorError(
            "repo has no scripts/agent_workflow — install the workflow kit to author stories"
        )
    # The tool takes exactly one parent mode: an epic ID positional XOR
    # --standalone. Sending both, or neither, is a usage error it rejects.
    parent = ["--standalone"] if data.epic_id is None else [data.epic_id]
    try:
        result = subprocess.run(
            [str(command), "create-story", *parent,
             "--title", data.title, "--coordination-class", data.coordination_class],
            cwd=root, capture_output=True, text=True, timeout=_TIMEOUT_SECONDS, check=False,
        )
    # Same strict-decode exposure as the snapshot read above.
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError) as exc:
        raise WorkflowReadError(f"create-story failed: {exc}") from exc
    if result.returncode != 0:
        raise WorkflowReadError(
            f"create-story failed: {(result.stderr or result.stdout).strip()[:300]}"
        )
    try:
        story = json.loads(result.stdout)["story"]
        authored = AuthoredStory(
            story_id=story["story_id"], epic_id=story["epic_id"],
            coordination_class=story["coordination_class"], state=story["state"],
            title=story["title"], path=story["path"],
        )
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise WorkflowReadError("create-story emitted an unexpected payload") from exc

    if data.body:
        path = _safe_ticket_path(root, authored.path)
        path.write_text(_merge_story_body(path.read_text(), data.body))
    return authored


def _merge_story_body(skeleton: str, body: str) -> str:
    """Keep the tool's title/Identity/Status header; replace everything from
    `## Story` down with the shaped body. A `## Status` section arriving in the
    body is reconciled into the skeleton's block, never appended beside it —
    the portable tools read the first status match in the file, so a second
    block is not clutter but a stale answer sitting in front of the real one."""
    body, incoming_status = _split_status_section(body)
    head, _, _ = skeleton.partition("\n## Story\n")
    head = _reconcile_status(head, incoming_status)
    content = body.strip()
    if not content.startswith("#"):
        content = "## Story\n\n" + content
    return head.rstrip() + "\n\n" + content + "\n"


_STATUS_SECTION = re.compile(r"^## Status[ \t]*$\n.*?(?=^## |\Z)", re.MULTILINE | re.DOTALL)
_STATUS_LINE = re.compile(r"^- (?P<field>[A-Za-z][A-Za-z ]*):[ \t]*(?P<value>.*)$", re.MULTILINE)
#: Same shape the portable contract uses to ignore documented examples: a
#: fenced ``` block is prose about the format, never the format itself.
_FENCED_BLOCK = re.compile(
    r"^(?P<fence>```+|~~~+).*?(?:^(?P=fence)[ \t]*$|\Z)", re.MULTILINE | re.DOTALL
)
_STATUS_PLACEHOLDER = "—"

#: History facts worth carrying across a merge. Lifecycle fields (State, Phase)
#: are deliberately NOT carried: the story re-enters the lifecycle where the
#: file now lives, and legacy phase vocabulary ("review-ready") is exactly what
#: the portable closer rejects.
_CARRIED_STATUS_FIELDS = ("Started", "Completed")


def _mask_fenced_blocks(text: str) -> str:
    """Blank fenced content, preserving offsets, so section matches on the
    masked text slice back into the original."""
    return _FENCED_BLOCK.sub(
        lambda m: "".join("\n" if c == "\n" else " " for c in m.group(0)), text
    )


def _split_status_section(body: str) -> tuple[str, dict[str, str]]:
    """Strip every real `## Status` section from the body; return its field
    values, first occurrence winning. A fenced status example is documentation
    and stays exactly where it is."""
    fields: dict[str, str] = {}
    while True:
        masked = _mask_fenced_blocks(body)
        match = _STATUS_SECTION.search(masked)
        if match is None:
            return body, fields
        for line in _STATUS_LINE.finditer(masked[match.start():match.end()]):
            fields.setdefault(line.group("field"), line.group("value").strip())
        body = body[: match.start()] + body[match.end():]


def _reconcile_status(head: str, incoming: dict[str, str]) -> str:
    """Fill the skeleton's placeholder fields from the incoming status. Only
    placeholders: a real skeleton value is never overwritten."""
    for field in _CARRIED_STATUS_FIELDS:
        value = incoming.get(field, "")
        if value and value != _STATUS_PLACEHOLDER:
            head = re.sub(
                rf"^- {field}: {_STATUS_PLACEHOLDER}$",
                lambda _, field=field, value=value: f"- {field}: {value}",
                head, count=1, flags=re.MULTILINE,
            )
    return head


def adopt_legacy(
    repo_path: str, legacy_id: str, epic_id: str | None, coordination_class: str
) -> AuthoredStory:
    """Explicit, human-triggered migration of one legacy ticket into a story,
    under an epic or standalone. The legacy file is removed only after the
    story exists — a tool failure loses nothing."""
    root = Path(repo_path).resolve()
    workflow = load_workflow(repo_path)
    item = next((x for x in workflow.legacy if x.legacy_id == legacy_id), None)
    if item is None:
        raise WorkflowDocumentError(f"legacy ticket {legacy_id!r} not found")
    source = _safe_ticket_path(root, item.path)
    title, body = _split_title(source.read_text(), fallback=item.title)

    authored = create_story(repo_path, StoryCreateIn(
        epic_id=epic_id, coordination_class=coordination_class,  # type: ignore[arg-type]
        title=title, body=body or None,
    ))
    source.unlink()
    return authored


def _split_title(content: str, fallback: str) -> tuple[str, str]:
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("# "):
            return line[2:].strip(), "\n".join(lines[i + 1:]).strip()
    return fallback, content.strip()


def mark_ready(repo_path: str, story_id: str) -> AuthoredStory:
    """The backlog -> ready promotion: an atomic move that preserves identity
    and updates the Status block, exactly as the contract prescribes."""
    root = Path(repo_path).resolve()
    workflow = load_workflow(repo_path)
    story = next((s for s in workflow.stories if s.story_id == story_id), None)
    if story is None:
        raise WorkflowDocumentError(f"story {story_id!r} not found")
    if story.state != "backlog":
        raise WorkflowAuthorError(f"story {story_id} is {story.state!r}, only backlog promotes")

    source = _safe_ticket_path(root, story.path)
    text = source.read_text()
    text = re.sub(r"^- State: .*$", "- State: ready", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^- Phase: .*$", "- Phase: queued", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^- Updated: .*$", f"- Updated: {date.today().isoformat()}",
                  text, count=1, flags=re.MULTILINE)
    dest_dir = root / "tickets" / "ready"
    dest_dir.mkdir(exist_ok=True)
    (dest_dir / source.name).write_text(text)
    source.unlink()
    return AuthoredStory(
        story_id=story.story_id, epic_id=story.epic_id,
        coordination_class=story.coordination_class, state="ready",
        title=story.title, path=f"tickets/ready/{source.name}",
    )


def _legacy_projection(root: Path) -> WorkflowProjection:
    legacy = [
        WorkflowLegacy(
            kind="legacy",
            legacy_id=ticket.slug,
            title=ticket.title,
            path=f"tickets/{ticket.slug}.md",
            state=None,
        )
        for ticket in list_tickets(str(root))
    ]
    return WorkflowProjection(
        source="legacy-flat",
        schema_version=None,
        ticket_contract=None,
        epics=[],
        stories=[],
        legacy=legacy,
        runs=[],
        diagnostics=[],
    )


def _safe_ticket_path(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute() or relative.suffix != ".md":
        raise WorkflowDocumentError(f"unsafe workflow locator: {locator!r}")
    tickets = (root / "tickets").resolve()
    path = (root / relative).resolve()
    if not path.is_relative_to(tickets) or not path.is_file():
        raise WorkflowDocumentError(f"missing or unsafe workflow locator: {locator!r}")
    return path
