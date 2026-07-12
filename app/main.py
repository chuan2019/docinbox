from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from botocore.exceptions import BotoCoreError, ClientError

from app.aws.clients import get_client

app = FastAPI(title="Smart Document Inbox")


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

