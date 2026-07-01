from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str

    model_config = {"env_prefix": "AGENTIC_CONTROL_PLANE_", "env_file": ".env"}


settings = Settings()
