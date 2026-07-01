from pathlib import Path

from pydantic_settings import BaseSettings

# apps/api/.env — anchored absolutely so it resolves regardless of CWD
# (tests and `make serve` both run from the repo root).
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    database_url: str
    # Bearer token required on every /api route. Override in .env for anything
    # reachable beyond localhost (Tailscale, LAN).
    auth_token: str = "dev-token"

    model_config = {"env_prefix": "AGENTIC_CONTROL_PLANE_", "env_file": str(_ENV_FILE)}


settings = Settings()
