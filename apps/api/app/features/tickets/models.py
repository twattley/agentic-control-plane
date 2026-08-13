from pydantic import BaseModel, Field


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


class TicketCreate(BaseModel):
    # A slug is a filename stem, never a path: letters/digits/dot/dash/underscore,
    # not starting with a dot. The regex is the write-path traversal guard.
    slug: str = Field(pattern=r"^[A-Za-z0-9_-][A-Za-z0-9._-]*$")
    content: str


class TicketUpdate(BaseModel):
    content: str
