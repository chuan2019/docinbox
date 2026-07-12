from unittest.mock import MagicMock

from botocore.exceptions import ClientError


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
