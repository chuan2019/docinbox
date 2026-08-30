from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from fastapi import HTTPException
from pydantic import SecretStr

from app.app_config import AppConfig
from app.main import app, get_repository
from app.repository import DocumentRepository


def test_healthz_ok_when_aws_reachable(client):
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "account" in body


def test_healthz_unhealthy_when_aws_unreachable(client, monkeypatch):
    broken_client = MagicMock()
    broken_client.get_caller_identity.side_effect = ClientError(
        {"Error": {"Code": "InvalidClientTokenId", "Message": "boom"}},
        "GetCallerIdentity",
    )
    monkeypatch.setattr("app.main.get_client", lambda _service: broken_client)

    resp = client.get("/healthz")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "unhealthy"
    assert "error" in body


def test_create_bucket(client):
    resp = client.post("/buckets/my-bucket")
    assert resp.status_code == 200
    assert resp.json() == {"created": "my-bucket"}


def test_create_bucket_is_idempotent(client):
    first = client.post("/buckets/my-bucket")
    second = client.post("/buckets/my-bucket")
    assert first.status_code == second.status_code == 200


def test_list_buckets_reports_created_buckets(client):
    client.post("/buckets/alpha")
    client.post("/buckets/beta")

    resp = client.get("/buckets")

    assert resp.status_code == 200
    assert set(resp.json()["buckets"]) == {"alpha", "beta"}


def test_list_buckets_empty_when_none_created(client):
    resp = client.get("/buckets")
    assert resp.status_code == 200
    assert resp.json() == {"buckets": []}


def test_delete_bucket(client):
    client.post("/buckets/my-bucket")

    resp = client.delete("/buckets/my-bucket")

    assert resp.status_code == 200
    assert resp.json() == {"deleted": "my-bucket"}
    assert client.get("/buckets").json() == {"buckets": []}


def test_delete_bucket_is_idempotent_when_missing(client):
    resp = client.delete("/buckets/never-created")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": "never-created"}


def test_delete_bucket_conflicts_when_not_empty(client):
    from app.aws.clients import get_client

    client.post("/buckets/my-bucket")
    get_client("s3").put_object(Bucket="my-bucket", Key="doc.txt", Body=b"hi")

    resp = client.delete("/buckets/my-bucket")

    assert resp.status_code == 409
    assert "not empty" in resp.json()["detail"]
    assert client.get("/buckets").json() == {"buckets": ["my-bucket"]}


def _config() -> AppConfig:
    return AppConfig(
        bucket_name="inbox-uploads",
        table_name="docinbox",
        llm_model="claude-opus-5",
        email_digest_enabled=False,
        signing_key=SecretStr("k"),
    )


def test_get_repository_is_unavailable_before_startup(monkeypatch):
    """
    app.state.dynamodb only exists once the lifespan has run. Reading it
    unguarded made that a bare AttributeError 500 from inside a dependency.
    """
    monkeypatch.delattr(app.state, "dynamodb", raising=False)

    with pytest.raises(HTTPException) as excinfo:
        get_repository(config=_config())

    assert excinfo.value.status_code == 503
    assert "startup" in excinfo.value.detail


def test_get_repository_builds_a_repository_after_startup(client):
    """The `client` fixture runs the lifespan, so the client is live."""
    assert isinstance(get_repository(config=_config()), DocumentRepository)
