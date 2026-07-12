from functools import lru_cache
from typing import Any

import boto3


from app.config import get_settings


def _client_kwargs() -> dict[str, Any]:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "region_name": settings.aws_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
    }
    # Only override the endpoint when configured (i.e. local dev).
    # In production this stays unset and boto3 targets real AWS.
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return kwargs


@lru_cache
def get_client(service: str) -> Any:
    """Return a cached boto3 client for `service`, wired to MiniStack or AWS.

    boto3 clients are thread-safe, so caching one per service is both safe
    and the recommended pattern (client creation is relatively expensive).
    """
    return boto3.client(service, **_client_kwargs())

