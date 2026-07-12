from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, read from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Set to http://localhost:4566 locally; LEAVE UNSET in real AWS
    aws_endpoint_url: str | None = None
    aws_region: str = "us-east-1"

    # MiniStack ignores these; real AWS uses the ambient credential chain
    # (IAM role, SSO, etc.) and ignores these defaults
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so we parse the environment once."""
    return Settings()

