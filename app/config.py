from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Bootstrap configuration, read from environment / .env.
    Only what we need BEFORE we can talk to AWS. Everything else
    (bucket names, model names, flags) lives in SSM - see app_config.py.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    # Set to http://localhost:4566 locally; LEAVE UNSET in real AWS
    aws_endpoint_url: str | None = None
    aws_region: str = "us-east-1"
    aws_access_key_id: str = "test"
    aws_secret_access_key: str = "test"
    # Which config tree to read: /docinbox/<app_env>/...
    app_env: str = "dev"
    # How long loaded app config stays fresh before we re-fetch.
    config_ttl_seconds: int = 300
    # Exposes GET /config. Never enable in production.
    debug_routes: bool = True

@lru_cache
def get_settings() -> Settings:
    """Cached singleton so we parse the environment once."""
    return Settings()
