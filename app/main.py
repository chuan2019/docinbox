from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from botocore.exceptions import BotoCoreError, ClientError
from app.app_config import AppConfig, ConfigCache
from app.aws.clients import get_client
from app.config import get_settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast: if SSM/Secrets Manager is unreachable or a parameter is
    # missing, the app fails at startup instead of at request time.
    cache = ConfigCache(ttl_seconds=get_settings().config_ttl_seconds)
    cache.get()  # first fetch happens here, at startup
    app.state.config_cache = cache
    yield


app = FastAPI(title="Smart Document Inbox")


def get_app_config() -> AppConfig:
    """FastAPI dependency: current app config (cached, TTL-refreshed)."""
    return app.state.config_cache.get()


@app.get("/whoami")
def whoami() -> dict[str, str]:
    """Who does AWS think we are? (STS GetCallerIdentity)"""
    identity = get_client("sts").get_caller_identity()
    return {
        "account": identity["Account"],
        "arn": identity["Arn"],
        "user_id": identity["UserId"],
    }


@app.get("/config")
def show_config(config: AppConfig = Depends(get_app_config)) -> dict[str, str | bool]:
    """Resolved app config - non-secret values only. Guarded by DEBUG_ROUTES."""
    if not get_settings().debug_routes:
        raise HTTPException(status_code=404)  # 404, not 403: don't advertise it
    return {
        "app_env": get_settings().app_env,
        "bucket_name": config.bucket_name,
        "llm_model": config.llm_model,
        "email_digest_enabled": config.email_digest_enabled,
        # SecretStr masks itself - this serializes as "**********".
        "signing_key": str(config.signing_key),
    }


@app.get("/healthz")
def healthz() -> JSONResponse:
    """Liveness + AWS reachability

    Response 200 only if we can make a real (emulated) AWS call.
    """
    try:
        identity = get_client("sts").get_caller_identity()
    except (ClientError, BotoCoreError) as exc:
        # Reaching AWS/MiniStack failed - report unhealthy, don't crash
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(exc)},
        )
    return JSONResponse(
        content={"status": "ok", "account": identity["Account"]}
    )



@app.post("/buckets/{name}")
def create_bucket(name: str) -> dict[str, str]:
    """Create an S3 bucket - our first real write to (emulated) AWS."""
    s3 = get_client("s3")
    try:
        s3.create_bucket(Bucket=name)
    except s3.exceptions.BucketAlreadyOwnedByYou:
        pass  # idempotent: fine if it already exists
    return {"created": name}


@app.get("/buckets")
def list_buckets() -> dict[str, list[str]]:
    s3 = get_client("s3")
    resp = s3.list_buckets()
    return {"buckets": [b["Name"] for b in resp["Buckets"]]}


@app.delete("/buckets/{name}")
def delete_bucket(name: str) -> dict[str, str]:
    """Delete an S3 bucket. Idempotent: fine if it's already gone."""
    s3 = get_client("s3")
    try:
        s3.delete_bucket(Bucket=name)
    except s3.exceptions.NoSuchBucket:
        pass
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "BucketNotEmpty":
            raise HTTPException(
                status_code=409, detail=f"bucket '{name}' is not empty"
            ) from exc
        raise
    return {"deleted": name}

