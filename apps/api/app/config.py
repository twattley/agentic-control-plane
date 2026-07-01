from pathlib import Path

from pydantic_settings import BaseSettings

# apps/api/.env — anchored absolutely so it resolves regardless of CWD
# (tests and `make serve` both run from the repo root).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

_DEFAULT_PROJECTS_ROOT = str(Path.home() / "Projects")


class Settings(BaseSettings):
    database_url: str
    # Bearer token required on every /api route. Override in .env for anything
    # reachable beyond localhost (Tailscale, LAN).
    auth_token: str = "dev-token"

    # Auto-dispatch the next agent on each state transition. Off by default so
    # tests and read-only use never spawn processes; on for the live service.
    dispatch_enabled: bool = False
    # Which provider runs each role. Flip to real CLIs on a real checkout;
    # "stub" runs a fake agent (a tiny repo edit) to prove the chain safely.
    builder_provider: str = "stub"
    reviewer_provider: str = "stub"
    # Where a finished worker kicks the API to dispatch the next agent.
    api_url: str = "http://127.0.0.1:8400"
    # Max "changes" verdicts before the reviewer escalates to the human instead
    # of bouncing the run back to the builder — bounds build<->review spend.
    max_review_rounds: int = 2
    # Shell command the closer runs as the gate before committing (must exit 0).
    # Default is a no-op; set to the repo's test command to gate on green tests.
    close_gate_command: str = "true"
    # Root folder whose subdirectories are the registerable projects. The
    # register UI offers a dropdown of these — no free-text paths.
    projects_root: str = _DEFAULT_PROJECTS_ROOT

    model_config = {"env_prefix": "AGENTIC_CONTROL_PLANE_", "env_file": str(_ENV_FILE)}


# Which role owns each "waiting" state — i.e. who gets dispatched when a run
# lands here. Active states (building/reviewing/fixing) are already owned.
ROLE_FOR_STATE = {
    "queued": "builder",
    "needs_work": "builder",
    "awaiting_review": "reviewer",
    "closing": "closer",
}


settings = Settings()
