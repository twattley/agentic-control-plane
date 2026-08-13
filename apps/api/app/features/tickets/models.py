from pydantic import BaseModel


class Ticket(BaseModel):
    slug: str          # filename without .md — doubles as the run's ticket_id
    title: str         # first `# ` heading, falling back to the slug


class TicketDetail(BaseModel):
    slug: str
    title: str
    content: str       # raw markdown
