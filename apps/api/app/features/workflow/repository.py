import json
import subprocess
from pathlib import Path

from pydantic import ValidationError

from app.features.tickets.repository import list_tickets, ticket_summary
from app.features.workflow.models import (
    WorkflowDocument,
    WorkflowLegacy,
    WorkflowProjection,
    WorkflowSnapshot,
)

_SCHEMA_VERSION = "agent-workflow-snapshot-v1"
_TIMEOUT_SECONDS = 5


class WorkflowReadError(Exception):
    """A present adapter failed to provide the exact supported snapshot."""


class WorkflowDocumentError(Exception):
    """A stable identity did not resolve to one safe current document."""


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
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkflowReadError(f"workflow snapshot command failed: {exc}") from exc

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise WorkflowReadError("workflow snapshot emitted invalid JSON") from exc
    if not isinstance(raw, dict):
        raise WorkflowReadError("workflow snapshot must be a JSON object")
    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise WorkflowReadError(
            f"unsupported workflow schema: {raw.get('schema_version')!r}"
        )

    try:
        snapshot = WorkflowSnapshot.model_validate(raw)
    except ValidationError as exc:
        raise WorkflowReadError(f"invalid workflow snapshot: {exc}") from exc
    return WorkflowProjection(
        source=_SCHEMA_VERSION,
        **snapshot.model_dump(),
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
