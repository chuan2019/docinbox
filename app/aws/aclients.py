"""
The async counterpart to clients.py - for the I/O worth overlapping.
boto3 clients (clients.py) are cheap and reused everywhere.
aioboto3 clients hold an open aiohttp session and must be opened as an
async context manager, so this module hands one out tied to an
AsyncExitStack the caller owns (in practice: the app lifespan).
"""
from contextlib import AsyncExitStack, AsyncExitStack
from typing import Any
import aioboto3
from botocore.config import Config
from app.config import get_settings

# Path-style addressing: with the virtual-hosted default, a presigned URL
# would point at http://inbox-uploads.localhost:4566/..., which nothing 
# resolves. Path-style keeps the bucket name in the path instead.
_S3_ADDRESSING = Config(s3={"addressing_style": "path"})
_session = aioboto3.Session()

def _client_kwargs() -> dict[str, Any]:
    settings = get_settings()
    kwargs: dict[str, Any] = {
        "region_name": settings.aws_region,
        "aws_access_key_id": settings.aws_access_key_id,
        "aws_secret_access_key": settings.aws_secret_access_key,
        "config": _S3_ADDRESSING,
    }
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return kwargs

async def open_async_client(stack: AsyncExitStack, service: str) -> Any:
    """
    Open an async client for `service`, tied to `stack`'s lifetime.
    Call this once (the app lifespan does) and reuse the client it
    returns - aioboto3 clients are not meant to be opened per request.
    """
    return await stack.enter_async_context(
        _session.client(service, **_client_kwargs())
    )