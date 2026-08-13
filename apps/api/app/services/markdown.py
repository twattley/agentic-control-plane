"""Tiny markdown readers for the two places the plane derives text from files:
README project blurbs and ticket summaries. Read-only, no rendering."""


def first_prose_paragraph(text: str, cap: int = 220) -> str | None:
    """The first prose paragraph, joined to one line. Headings, badges, images,
    rules and fenced code are skipped; a blockquote tagline counts as prose."""
    para: list[str] = []
    in_fence = False
    for raw in text.splitlines():
        line = raw.strip().removeprefix("> ").strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if not line or line.startswith(("#", "![", "[!", "---", "===")):
            if para:
                break
            continue
        para.append(line)
    if not para:
        return None
    joined = " ".join(para)
    return joined[: cap - 3] + "…" if len(joined) > cap else joined


def section(text: str, heading: str) -> str | None:
    """The body of the `## <heading>` section (any heading level), up to the
    next heading. None when the section doesn't exist."""
    lines: list[str] = []
    in_section = False
    for raw in text.splitlines():
        stripped = raw.strip()
        if stripped.startswith("#"):
            if in_section:
                break
            in_section = stripped.lstrip("#").strip().lower() == heading.lower()
            continue
        if in_section:
            lines.append(raw)
    body = "\n".join(lines).strip()
    return body or None
