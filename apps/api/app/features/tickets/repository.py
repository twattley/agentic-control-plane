"""Tickets are markdown files in `tickets/` at the repo checkout root.

The checkout is the source of truth — the control plane reads it, never writes.
No tables: a ticket becomes a row only when a run is started from it.
"""

from pathlib import Path

from app.features.tickets.models import Ticket, TicketDetail


def list_tickets(repo_path: str) -> list[Ticket]:
    folder = Path(repo_path) / "tickets"
    if not folder.is_dir():
        return []
    return [Ticket(slug=p.stem, title=_title(p)) for p in sorted(folder.glob("*.md"))]


def get_ticket(repo_path: str, slug: str) -> TicketDetail | None:
    path = _resolve(repo_path, slug)
    if path is None:
        return None
    return TicketDetail(slug=slug, title=_title(path), content=path.read_text())


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
