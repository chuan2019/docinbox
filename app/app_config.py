"""
Application config, loaded from SSM Parameter Store + Secrets Manager.
Bootstrap settings (endpoint, region, env) come from the environment -
see config.py. Everything here comes from AWS at runtime.
"""
import time
from pydantic import BaseModel, SecretStr
from app.aws.clients import get_client
from app.config import get_settings


class AppConfig(BaseModel):
    """Validated application configuration."""
    bucket_name: str
    llm_model: str
    email_digest_enabled: bool
    signing_key: SecretStr  # renders as '**********' in logs and repr

def _load_parameters(prefix: str) -> dict[str, str]:
    """Fetch every parameter under `prefix` as {relative-name: value}."""
    ssm = get_client("ssm")
    params: dict[str, str] = {}
    paginator = ssm.get_paginator("get_parameters_by_path")
    for page in paginator.paginate(
        Path=prefix,
        Recursive=True,
        WithDecryption=True
    ):
        for param in page["Parameters"]:
            params[param["Name"].removeprefix(prefix + "/")] = param["Value"]
    return params

def _load_signing_key(env: str) -> SecretStr:
    sm = get_client("Secretsmanager")
    resp = sm.get_secret_value(SecretId=f"docinbox/{env}/signing-key")
    return SecretStr(resp["SecretString"])

def load_app_config() -> AppConfig:
    """One startup-time round trip to SSM + one to Secrets Manager."""
    env = get_settings().app_env
    params = _load_parameters(f"/docinbox/{env}")
    return AppConfig(
        bucket_name=params["s3/bucket-name"],
        llm_model=params["llm/model-name"],
        email_digest_enabled=params.get("features/email-digest") == "true",
        signing_key=_load_signing_key(env),
    )


class ConfigCache:
    """Holds AppConfig in memory, re-fetching when older than the TTL."""
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._config: AppConfig | None = None
        self._loaded_at = 0.0
    
    def get(self) -> AppConfig:
        if self._config is None or time.monotonic() - self._loaded_at > self._ttl:
            self._config = load_app_config()
            self._loaded_at = time.monotonic()
        return self._config

def invalidate(self) -> None:
    """Force a re-fetch on the next get() - used by tests (and an exercise)."""
    self._config = None
