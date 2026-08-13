from pydantic import BaseModel


class Ticket(BaseModel):
    slug: str          # filename without .md — doubles as the run's ticket_id
    title: str         # first `# ` heading, falling back to the slug
    # The re-entry blurb: the `## Summary` section written when the ticket was
    # frozen, falling back to the first prose paragraph. None for a bare file.
    summary: str | None = None


class TicketDetail(BaseModel):
    slug: str
    title: str
    summary: str | None = None
    content: str       # raw markdown
