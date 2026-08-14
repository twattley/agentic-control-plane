"""One turn of a ticket-shaping discussion = one short-lived `claude -p` run
in the repo checkout, resumed across turns via the CLI's session id.

Read-only by construction: no permission mode is granted, so in print mode
every write tool is auto-denied — the shaping agent can read the codebase but
never touch it. The plane writes the frozen ticket itself through the tickets
feature, keeping `tickets/` the single write surface.
"""

import asyncio
import json

_SYSTEM = (
    "You are shaping a work ticket for this repository through a short dialogue "
    "with its owner. Ground every answer in the actual code — read files when it "
    "helps. Ask the one or two questions that most reduce ambiguity, challenge "
    "scope that looks too big, and keep replies under 150 words. Never write files."
)

FREEZE_PROMPT = (
    "Freeze the ticket now. Reply with ONLY the ticket markdown, no preamble: a "
    "`# <title>` line, then a `## Summary` section of two or three sentences "
    "aimed at someone re-entering this work cold, then `## Done means` with the "
    "concrete, checkable scenarios from our discussion."
)

_TIMEOUT_S = 180


class AgentError(Exception):
    """The shaping agent failed or timed out; the turn was not recorded."""


async def reply(repo_path: str, message: str, session_id: str | None) -> tuple[str, str]:
    """Run one agent turn in the checkout. Returns (session_id, reply_text)."""
    cmd = ["claude", "-p", message, "--output-format", "json",
           "--append-system-prompt", _SYSTEM]
    if session_id:
        cmd += ["--resume", session_id]
    proc = await asyncio.create_subprocess_exec(
        *cmd, cwd=repo_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=_TIMEOUT_S)
    except TimeoutError:
        proc.kill()
        raise AgentError("shaping agent timed out") from None
    if proc.returncode != 0:
        raise AgentError((err or out).decode(errors="replace")[:300])
    data = json.loads(out.decode())
    return data.get("session_id", session_id or ""), data.get("result", "").strip()


def strip_fence(text: str) -> str:
    """A freeze reply should be bare markdown; unwrap it if the model fenced it."""
    lines = text.strip().splitlines()
    if len(lines) >= 2 and lines[0].startswith("```") and lines[-1].startswith("```"):
        lines = lines[1:-1]
    return "\n".join(lines).strip() + "\n"
