"""Tickets are markdown files in `tickets/` at the repo checkout root.

The checkout is the source of truth. `tickets/` is the plane's ONE write
surface — the UI's ticket composer creates and edits files here; nothing else
in a checkout is ever written. No tables: a ticket becomes a row only when a
run is started from it.
"""

from pathlib import Path

from app.features.tickets.models import Ticket, TicketDetail
from app.services.markdown import first_prose_paragraph, section

# Files in tickets/ that are reference material, not startable work: all-caps
# single words (README, NOW — ticket ids like SBX-3 keep their dash/digits) and
# these prefixes.
_DOC_PREFIXES = ("handoff-", "plan-", "re-fresh-", "refresh-", "human-", "notes-")


def _kind(stem: str) -> str:
    if (stem.isalpha() and stem == stem.upper()) or stem.lower().startswith(_DOC_PREFIXES):
        return "doc"
    return "ticket"


def list_tickets(repo_path: str) -> list[Ticket]:
    folder = Path(repo_path) / "tickets"
    if not folder.is_dir():
        return []
    return [
        Ticket(slug=p.stem, title=_title(p), kind=_kind(p.stem), summary=ticket_summary(p))
        for p in sorted(folder.glob("*.md"))
    ]


def get_ticket(repo_path: str, slug: str) -> TicketDetail | None:
    path = _resolve(repo_path, slug)
    if path is None:
        return None
    return TicketDetail(
        slug=slug, title=_title(path), summary=ticket_summary(path), content=path.read_text()
    )


class TicketExistsError(Exception):
    """Create refused: the slug already has a file (edit goes through update)."""


def create_ticket(repo_path: str, slug: str, content: str) -> TicketDetail:
    folder = Path(repo_path) / "tickets"
    folder.mkdir(exist_ok=True)
    if _resolve(repo_path, slug) is not None:
        raise TicketExistsError(slug)
    (folder / f"{slug}.md").write_text(content)
    return get_ticket(repo_path, slug)  # type: ignore[return-value]


def update_ticket(repo_path: str, slug: str, content: str) -> TicketDetail | None:
    path = _resolve(repo_path, slug)
    if path is None:
        return None
    path.write_text(content)
    return get_ticket(repo_path, slug)


def ticket_summary(path: Path) -> str | None:
    """The re-entry blurb: the `## Summary` section (written at ticket freeze),
    else the file's first prose paragraph. Also used by the workbench board."""
    text = path.read_text()
    frozen = section(text, "Summary")
    return first_prose_paragraph(frozen if frozen is not None else text)


def _resolve(repo_path: str, slug: str) -> Path | None:
    """Map a slug to a file strictly inside tickets/ — a slug is a filename,
    never a path, so anything that escapes the folder resolves to None."""
    folder = (Path(repo_path) / "tickets").resolve()
    path = (folder / f"{slug}.md").resolve()
    if path.parent != folder or not path.is_file():
        return None
    return path


def _title(path: Path) -> str:
    for line in path.read_text().splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem
