import uuid
import base64
import json
import logging
from contextlib import AsyncExitStack, asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, File, UploadFile, Header
from fastapi.responses import JSONResponse, StreamingResponse
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel as RequestModel

from app.app_config import AppConfig, ConfigCache
from app.aws.clients import get_client
from app.config import get_settings
from app.aws.aclients import open_async_client
from app.models import DocumentRecord, DocumentStatus
from app.repository import DocumentRepository, StatusConflictError


logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast: if SSM/Secrets Manager is unreachable or a parameter is
    # missing, the app fails at startup instead of at request time.
    cache = ConfigCache(ttl_seconds=get_settings().config_ttl_seconds)
    cache.get()  # first fetch happens here, at startup
    app.state.config_cache = cache

    async with AsyncExitStack() as stack:
        app.state.s3 = await open_async_client(stack, "s3")
        app.state.dynamodb = await open_async_client(stack, "dynamodb")
        # Presigned URLs must name a host the CALLER can resolve, which is not
        # always the one we call ourselves (in Docker: `ministack` vs the
        # host's `localhost`). When the two differ, sign with a second client
        # bound to the public endpoint; it never issues a request, it only
        # signs. Unset in real AWS -> both names point at the same client.
        public_endpoint = get_settings().public_aws_endpoint_url
        app.state.s3_public = (
            await open_async_client(stack, "s3", endpoint_url=public_endpoint)
            if public_endpoint
            else app.state.s3
        )
        yield
    # the stack closes app.state.s3's aiohttp session on shutdown


app = FastAPI(title="Smart Document Inbox", lifespan=lifespan)


def get_app_config() -> AppConfig:
    """FastAPI dependency: current app config (cached, TTL-refreshed)."""
    return app.state.config_cache.get()


def get_repository(config: AppConfig = Depends(get_app_config)) -> DocumentRepository:
    """FastAPI dependency: a repository bound to the live client + table name."""
    # app.state.dynamodb only exists once the lifespan has run; without this
    # the miss is a bare AttributeError 500 from inside the dependency.
    client = getattr(app.state, "dynamodb", None)
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="DynamoDB client unavailable - app startup did not complete",
        )
    return DocumentRepository(client, config.table_name)


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
    x_owner: str = Header("demo@example.com", alias="X-Owner"),
    config: AppConfig = Depends(get_app_config),
    repo: DocumentRepository = Depends(get_repository),
) -> DocumentRecord:
    """
    Upload a document to S3. The document id is a new key, not the filename.
    """
    record = DocumentRecord(
        document_id=str(uuid.uuid4()),
        owner=x_owner,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "application/octet-stream",
        size=file.size or 0,
    )
    # S3 keeps the bytes (Part 3); DynamoDB keeps what we know about them.
    await app.state.s3.upload_fileobj(
        file.file,
        config.bucket_name,
        record.document_id,
        ExtraArgs={"ContentType": record.content_type},
    )
    await repo.create(record)
    return record


def _encode_token(key: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(key).encode()).decode()

def _decode_token(token: str) -> dict:
    try:
        return json.loads(base64.urlsafe_b64decode(token))
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="invalid next_token"
        ) from exc

@app.get("/documents")
async def list_documents(
    x_owner: str = Header("demo@example.com", alias="X-Owner"),
    limit: int = 20,
    next_token: str | None = None,
    repo: DocumentRepository = Depends(get_repository),
) -> dict:
    """
    List documents in the S3 bucket.
    """
    start_key = _decode_token(next_token) if next_token else None
    records, last_key = await repo.list_by_owner(
        owner=x_owner,
        limit=limit,
        start_key=start_key
    )
    return {
        "documents": records,
        "next_token": _encode_token(last_key) if last_key else None,
    }

@app.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    repo: DocumentRepository = Depends(get_repository),
) -> DocumentRecord:
    record = await repo.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="document not found")
    return record

@app.get("/documents/{document_id}/history")
async def get_document_history(
    document_id: str,
    repo: DocumentRepository = Depends(get_repository),
) -> dict:
    return {"events": await repo.history(document_id)}


class StatusChange(RequestModel):
    to: DocumentStatus
    detail: str = ""

@app.post("/documents/{document_id}/status")
async def change_status(
    document_id: str,
    change: StatusChange,
    repo: DocumentRepository = Depends(get_repository),
) -> DocumentRecord | None:
    """
    Simulate the worker's status transition. Debug-only until Part 5.
    """
    if not get_settings().debug_routes:
        raise HTTPException(status_code=404)  # 404, not 403: don't advertise it
    record = await repo.get(document_id)
    if record is None:
        raise HTTPException(status_code=404, detail="document not found")
    try:
        await repo.update_status(
            document_id=document_id,
            to_status=change.to,
            expected=record.status,
            detail=change.detail,
        )
    except StatusConflictError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc)
        ) from exc
    return await repo.get(document_id)


@app.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    config: AppConfig = Depends(get_app_config),
    repo: DocumentRepository = Depends(get_repository),
) -> StreamingResponse:
    """
    Generate a presigned URL to download a document from S3.
    """
    record = await repo.get(document_id)
    filename = record.filename if record and record.filename else document_id
    logger.info(f"download_document: document_id={document_id}, filename={filename}")
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

    logger.info(f"download_document: S3 object found, filename={filename}")
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

    # Signed by the public-endpoint client: no I/O, just a URL the caller
    # can follow. head_object above deliberately used the internal one.
    url = await app.state.s3_public.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.bucket_name, "Key": document_id},
        ExpiresIn=300,
    )
    return {"url": url, "expires_in": 300}
