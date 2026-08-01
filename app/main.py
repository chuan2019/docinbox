from contextlib import AsyncExitStack, asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from botocore.exceptions import BotoCoreError, ClientError
import uuid

from app.app_config import AppConfig, ConfigCache
from app.aws.clients import get_client
from app.config import get_settings
from app.aws.aclients import open_async_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast: if SSM/Secrets Manager is unreachable or a parameter is
    # missing, the app fails at startup instead of at request time.
    cache = ConfigCache(ttl_seconds=get_settings().config_ttl_seconds)
    cache.get()  # first fetch happens here, at startup
    app.state.config_cache = cache

    async with AsyncExitStack() as stack:
        app.state.s3 = await open_async_client(stack, "s3")
        yield
    # the stack closes app.state.s3's aiohttp session on shutdown


app = FastAPI(title="Smart Document Inbox", lifespan=lifespan)


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


@app.post("/documents", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    config: AppConfig = Depends(get_app_config)
) -> dict[str, str]:
    """
    Upload a document to S3. The document id is a new key, not the filename.
    """
    document_id = str(uuid.uuid4())
    content_type = file.content_type or "application/octet-stream"

    # upload_fileobj picks simple vs multipart based on size - we don't.
    await app.state.s3.upload_fileobj(
        file.file,
        config.bucket_name,
        document_id,
        ExtraArgs={
            "ContentType": content_type,
            "Metadata": {"filename": file.filename or "unnamed"},
        }
    )
    return {
        "document_id": document_id,
        "filename": file.filename or "unnamed",
        "content_type": content_type,
    }


@app.get("/documents")
async def list_documents(
    config: AppConfig = Depends(get_app_config)
) -> dict[str, list[dict[str, str | int]]]:
    """
    List documents in the S3 bucket.
    """
    resp = await app.state.s3.list_objects_v2(Bucket=config.bucket_name)
    documents = [
        {
            "document_id": obj["Key"],
            "size": obj["Size"],
            "last_modified": obj["LastModified"].isoformat(),
        }
        for obj in resp.get("Contents", [])
    ]
    return {"documents": documents}


@app.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    config: AppConfig = Depends(get_app_config)
) -> StreamingResponse:
    """
    Generate a presigned URL to download a document from S3.
    """
    try:
        obj = await app.state.s3.get_object(
            Bucket=config.bucket_name,
            Key=document_id
        )
    except app.state.s3.exceptions.NoSuchKey as exc:
        raise HTTPException(
            status_code=404,
            detail=f"document '{document_id}' not found"
        ) from exc

    filename = obj.get("Metadata", {}).get("filename", document_id)
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if "ContentLength" in obj:
        headers["Content-Length"] = str(obj["ContentLength"])

    return StreamingResponse(
        content=obj["Body"].iter_chunks(),
        media_type=obj.get("ContentType", "application/octet-stream"),
        headers=headers,
    )


@app.get("/documents/{document_id}/download_url")
async def download_document_url(
    document_id: str,
    config: AppConfig = Depends(get_app_config)
) -> dict[str, str | int]:
    """
    HeadObject confirms the key exists before we hand out a URL for it.
    """
    try:
        await app.state.s3.head_object(
            Bucket=config.bucket_name,
            Key=document_id,
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            raise HTTPException(
                status_code=404,
                detail=f"document '{document_id}' not found"
            ) from exc
        raise

    url = await app.state.s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.bucket_name, "Key": document_id},
        ExpiresIn=300,
    )
    return {"url": url, "expires_in": 300}
