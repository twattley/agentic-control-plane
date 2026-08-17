"""One turn of a ticket-shaping discussion = one short-lived `codex exec` run
in the repo checkout, resumed across turns via the CLI's thread id.

Read-only by construction: every initial and resumed command explicitly uses
the read-only sandbox. The shaping agent can inspect the codebase but never
touch it. The plane writes the frozen ticket itself through the tickets feature,
keeping `tickets/` the single write surface.
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

USER_SKILLS_DIR = Path.home() / ".claude" / "skills"

_SYSTEM = (
    "You are shaping a work ticket for this repository through a short dialogue "
    "with its owner. Size the request first as a chore, a small feature, or larger "
    "work. Read the relevant code and ground recommendations in exact files you "
    "actually read. For small, well-bounded work, make one confirming bounce and "
    "offer to freeze early. For fuzzy or larger work, use Given/When/Then scenario "
    "thinking, cover boundaries and an explicit should not happen, and challenge "
    "oversized scope. Ask one question at a time; always give a recommended answer "
    "and why. Before offering to freeze, establish the owner outcome, allowed_paths, "
    "and a runnable validation command; add forbidden_paths only for a real hazard. "
    "Keep replies under 150 words. Never write files."
)

FREEZE_PROMPT = (
    "Freeze the ticket now. Reply with ONLY ticket markdown and no preamble. Use "
    "`# <title>`, then `## Summary` with two or three cold-reentry sentences, "
    "`## Capability` with the owner-visible outcome, and, when the work is "
    "behavioral, `## Scenarios` with the Given/When/Then cases established in the "
    "discussion, including what should not happen. Add `## Scope` with a non-empty "
    "`allowed_paths` list, optional `read_context_paths`, and `forbidden_paths` only "
    "where a real hazard earned it. Add `## Validation` containing at least one "
    "runnable command in a fenced bash block. Finish with `## Done When` and a "
    "checklist of concrete, observable conditions. Do not invent unsettled details; "
    "if a required boundary or command is missing from the discussion, leave its "
    "required field or section empty so the plane can refuse the freeze."
)

_TIMEOUT_S = 180
_SESSION_PREFIX = "codex:"
_CODEX_PROFILE = (
    "--json",
    "-m", "gpt-5.6-sol",
    "-c", "model_reasoning_effort=high",
    "-c", "service_tier=priority",
)


class AgentError(Exception):
    """The shaping agent failed or timed out; the turn was not recorded."""


class SkillUnavailableError(Exception):
    """A requested installed skill cannot frame this discussion."""


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    description: str
    prompt: str


def _frontmatter_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def _skill_definition(skill_file: Path) -> SkillDefinition | None:
    try:
        prompt = skill_file.read_text()
    except OSError:
        return None
    lines = prompt.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        return None

    fields: dict[str, str] = {}
    frontmatter = lines[1:end]
    index = 0
    while index < len(frontmatter):
        line = frontmatter[index]
        key, separator, raw_value = line.partition(":")
        if line[:1].isspace() or not separator or key not in {"name", "description"}:
            index += 1
            continue
        value = raw_value.strip()
        if value in {">", ">-", "|", "|-"}:
            block: list[str] = []
            index += 1
            while index < len(frontmatter) and (
                frontmatter[index][:1].isspace() or not frontmatter[index].strip()
            ):
                if frontmatter[index].strip():
                    block.append(frontmatter[index].strip())
                index += 1
            fields[key] = " ".join(block) if value.startswith(">") else "\n".join(block)
            continue
        fields[key] = _frontmatter_value(value)
        index += 1

    if not fields.get("name") or not fields.get("description"):
        return None
    return SkillDefinition(
        name=fields["name"], description=fields["description"], prompt=prompt
    )


def discover_skills(repo_path: str) -> list[SkillDefinition]:
    """Read installed skills on every call; repo-local names override user names."""
    skills: dict[str, SkillDefinition] = {}
    roots = (USER_SKILLS_DIR, Path(repo_path) / ".claude" / "skills")
    for root in roots:
        for skill_file in sorted(root.glob("*/SKILL.md")):
            skill = _skill_definition(skill_file)
            if skill is not None:
                skills[skill.name] = skill
    return sorted(skills.values(), key=lambda skill: skill.name.casefold())


def resolve_skill(repo_path: str, skill_name: str | None) -> SkillDefinition | None:
    if skill_name is None:
        return None
    skill = next(
        (candidate for candidate in discover_skills(repo_path)
         if candidate.name == skill_name),
        None,
    )
    if skill is None:
        raise SkillUnavailableError(f"skill {skill_name!r} is not available")
    return skill


async def reply(
    repo_path: str,
    message: str,
    session_id: str | None,
    skill_prompt: str | None = None,
) -> tuple[str, str]:
    """Run one agent turn in the checkout. Returns (session_id, reply_text)."""
    resumed_thread_id = _resumed_thread_id(session_id)
    prompt = _SYSTEM
    if skill_prompt:
        prompt += f"\n\nUse this selected shaping skill:\n\n{skill_prompt}"
    prompt += f"\n\nThe owner's message for this turn is:\n\n{message}"

    cmd = ["codex", "exec", "-s", "read-only", "-C", repo_path,
           *_CODEX_PROFILE]
    if resumed_thread_id:
        cmd += ["resume", resumed_thread_id]
    cmd.append(prompt)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=repo_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise AgentError(f"could not start Codex: {detail}"[:300]) from None
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT_S)
    except TimeoutError:
        proc.kill()
        raise AgentError("shaping agent timed out") from None
    if proc.returncode != 0:
        detail = (err or out).decode(errors="replace").strip()
        raise AgentError((detail or "Codex shaping turn failed")[:300])
    return _codex_result(out, resumed_thread_id)


def _resumed_thread_id(session_id: str | None) -> str | None:
    if session_id is None:
        return None
    if not session_id.startswith(_SESSION_PREFIX):
        raise AgentError(
            "this discussion uses a legacy shaping session; start a new discussion"
        )
    thread_id = session_id.removeprefix(_SESSION_PREFIX)
    if not thread_id:
        raise AgentError("Codex returned an invalid response")
    return thread_id


def _codex_result(output: bytes, resumed_thread_id: str | None) -> tuple[str, str]:
    """Extract the resumable thread and final agent message from Codex JSONL."""
    thread_id = resumed_thread_id or ""
    reply_text = ""
    try:
        events = [json.loads(line) for line in output.decode().splitlines() if line]
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise AgentError("Codex returned an invalid response") from None

    for event in events:
        if not isinstance(event, dict):
            raise AgentError("Codex returned an invalid response")
        if event.get("type") == "thread.started":
            started_thread_id = event.get("thread_id", "")
            thread_id = started_thread_id if isinstance(started_thread_id, str) else ""
            continue
        item = event.get("item", {})
        if not isinstance(item, dict):
            continue
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            text = item.get("text", "")
            reply_text = text.strip() if isinstance(text, str) else ""

    if not thread_id or not reply_text:
        raise AgentError("Codex returned an invalid response")
    return f"{_SESSION_PREFIX}{thread_id}", reply_text


def strip_fence(text: str) -> str:
    """A freeze reply should be bare markdown; unwrap it if the model fenced it."""
    lines = text.strip().splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        lines = lines[1:-1]
    return "\n".join(lines).strip() + "\n"


def note_skill(markdown: str, skill_name: str | None) -> str:
    """Record shaping provenance without changing plain-conversation tickets."""
    if skill_name is None:
        return markdown
    lines = markdown.rstrip().splitlines()
    title_index = next(
        (index for index, line in enumerate(lines) if line.startswith("# ")),
        None,
    )
    if title_index is None:
        return markdown
    note = f"> Shaped with `{skill_name}`."
    body = lines[title_index + 1:]
    while body and not body[0].strip():
        body.pop(0)
    return "\n".join(lines[:title_index + 1] + ["", note, ""] + body) + "\n"
