"""
Guards on DocumentRepository's constructor arguments.

The repository is handed its client and table name by whoever builds it
(app.main.get_repository, in production). Everything here checks that a
wrong argument fails loudly at construction, rather than surfacing as a
500 from inside a request handler that has no handler for it.
"""
from unittest.mock import AsyncMock, MagicMock

import aioboto3
import boto3
import pytest
from botocore.exceptions import ClientError
from pydantic import SecretStr, ValidationError

from app.app_config import AppConfig
from app.models import DocumentStatus
from app.repository import DocumentRepository, StatusConflictError

TABLE = "docinbox"
# Region + credentials are needed to build a client; no call is ever made
# with them, so they don't have to be real (and moto isn't involved).
_CLIENT_KWARGS = {
    "region_name": "us-east-1",
    "aws_access_key_id": "testing",
    "aws_secret_access_key": "testing",
}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def ddb():
    """A real async DynamoDB client - opened, never called."""
    async with aioboto3.Session().client("dynamodb", **_CLIENT_KWARGS) as client:
        yield client


@pytest.fixture
async def s3():
    async with aioboto3.Session().client("s3", **_CLIENT_KWARGS) as client:
        yield client


@pytest.fixture
def fake_client():
    """A mock that satisfies the duck-type check - what a unit test passes."""
    client = MagicMock()
    for method in ("get_item", "put_item", "query", "transact_write_items"):
        setattr(client, method, AsyncMock())
    return client


# - the client guard - - - - - - - - - - - - - - - - - - - - - - - - - - -
def test_rejects_none_client():
    with pytest.raises(TypeError, match="get_item"):
        DocumentRepository(None, TABLE)


def test_rejects_sync_boto3_client():
    """
    The likeliest mix-up: clients.get_client instead of aclients'
    open_async_client. A sync client has every method we call, so without
    this check it only fails at `await <dict>`, mid-request.
    """
    sync_client = boto3.client("dynamodb", **_CLIENT_KWARGS)
    with pytest.raises(TypeError, match="synchronous"):
        DocumentRepository(sync_client, TABLE)


@pytest.mark.anyio
async def test_rejects_client_for_another_service(s3):
    with pytest.raises(TypeError):
        DocumentRepository(s3, TABLE)


@pytest.mark.anyio
async def test_accepts_async_dynamodb_client(ddb):
    assert DocumentRepository(ddb, TABLE)._table == TABLE


def test_accepts_duck_typed_fake(fake_client):
    assert DocumentRepository(fake_client, TABLE)


def test_rejects_fake_missing_a_method(fake_client):
    del fake_client.transact_write_items
    with pytest.raises(TypeError, match="transact_write_items"):
        DocumentRepository(fake_client, TABLE)


# - the table name guard - - - - - - - - - - - - - - - - - - - - - - - - -
@pytest.mark.parametrize(
    "name",
    [
        "",           # pydantic's plain `str` lets this through
        "   ",        # ...and this, which botocore lets through too
        "ab",         # under DynamoDB's 3-char minimum
        "a" * 256,    # over its 255-char maximum
        "my table",   # space is not in [A-Za-z0-9_.-]
        "table/name",
    ],
)
def test_rejects_malformed_table_name(fake_client, name):
    with pytest.raises(ValueError, match="invalid DynamoDB table name"):
        DocumentRepository(fake_client, name)


@pytest.mark.parametrize("name", [None, 123, b"docinbox"])
def test_rejects_non_string_table_name(fake_client, name):
    with pytest.raises(TypeError, match="must be a str"):
        DocumentRepository(fake_client, name)


@pytest.mark.parametrize("name", ["abc", "docinbox", "a-b.c_D9", "a" * 255])
def test_accepts_valid_table_name(fake_client, name):
    assert DocumentRepository(fake_client, name)._table == name


# - the pinned conflict exception - - - - - - - - - - - - - - - - - - - - -
@pytest.mark.anyio
async def test_uses_typed_exception_from_a_real_client(ddb):
    repo = DocumentRepository(ddb, TABLE)
    assert repo._conflict_exc is ddb.exceptions.TransactionCanceledException
    assert repo._conflict_is_typed


def test_falls_back_to_client_error_for_a_mock(fake_client):
    """
    A MagicMock resolves .exceptions.TransactionCanceledException to a
    Mock, which is not a class - so using it in an `except` clause raises
    TypeError. The fallback keeps the handler valid.
    """
    repo = DocumentRepository(fake_client, TABLE)
    assert repo._conflict_exc is ClientError
    assert not repo._conflict_is_typed


def _client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": "boom"}}, "TransactWriteItems"
    )


@pytest.mark.anyio
async def test_cancelled_transaction_becomes_a_status_conflict(fake_client):
    """Regression: this used to raise TypeError from the except clause."""
    fake_client.transact_write_items.side_effect = _client_error(
        "TransactionCanceledException"
    )
    repo = DocumentRepository(fake_client, TABLE)
    with pytest.raises(StatusConflictError, match="was not in status 'uploaded'"):
        await repo.update_status(
            "doc-1", DocumentStatus.PROCESSING, DocumentStatus.UPLOADED
        )


@pytest.mark.anyio
async def test_unrelated_client_error_still_propagates(fake_client):
    """The ClientError fallback must not swallow every other AWS error."""
    fake_client.transact_write_items.side_effect = _client_error(
        "ProvisionedThroughputExceededException"
    )
    repo = DocumentRepository(fake_client, TABLE)
    with pytest.raises(ClientError):
        await repo.update_status(
            "doc-1", DocumentStatus.PROCESSING, DocumentStatus.UPLOADED
        )


@pytest.mark.anyio
async def test_illegal_transition_never_reaches_the_client(fake_client):
    repo = DocumentRepository(fake_client, TABLE)
    with pytest.raises(StatusConflictError, match="illegal transition"):
        await repo.update_status(
            "doc-1", DocumentStatus.UPLOADED, DocumentStatus.PROCESSED
        )
    fake_client.transact_write_items.assert_not_awaited()


# - the same rule, one layer up - - - - - - - - - - - - - - - - - - - - - -
def _config(table_name: str) -> AppConfig:
    return AppConfig(
        bucket_name="inbox-uploads",
        table_name=table_name,
        llm_model="claude-opus-5",
        email_digest_enabled=False,
        signing_key=SecretStr("k"),
    )


@pytest.mark.parametrize("name", ["", "   ", "ab", "my table"])
def test_app_config_rejects_malformed_table_name(name):
    """Bad SSM config dies at startup, where load_app_config runs."""
    with pytest.raises(ValidationError):
        _config(name)


def test_app_config_accepts_a_valid_table_name():
    assert _config(TABLE).table_name == TABLE
