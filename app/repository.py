"""
DocumentRepository - every DynamoDB key decision in the app lives here.

Key design (the whole single-table layout, in one place):

    document:       PK=DOC#<id> SK=META             GSI1PK=OWNER#<owner>
                                                    GSI1SK=UPLOADED#<iso-ts>#<id>
    status event:   PK=DOC#<id> SK=EVENT#<iso-ts>   (no GSI keys - sparse)
"""
import re
from datetime import timedelta
from typing import Any

from aiobotocore.client import AioBaseClient
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from botocore.client import BaseClient
from botocore.exceptions import ClientError

from app.models import (
    VALID_TRANSITIONS,
    DocumentRecord,
    DocumentStatus,
    StatusEvent,
    utcnow,
)

_ser = TypeSerializer()
_de  = TypeDeserializer()

EVENT_TTL = timedelta(days=7) # status events clean themselves up

# DynamoDB's own rule: 3-255 chars of [A-Za-z0-9_.-]. botocore only checks
# 1-1024, so a too-short or oddly punctuated name would otherwise pass
# client-side validation and fail at the service - one wasted round trip
# per request, forever. app_config imports this so bad config dies at startup.
TABLE_NAME_PATTERN = r"^[A-Za-z0-9_.-]{3,255}$"
_TABLE_NAME_RE = re.compile(TABLE_NAME_PATTERN)

# The client methods this repository calls. Checked up front so a wrong
# object fails at construction, not halfway through a request.
_REQUIRED_CLIENT_METHODS = ("get_item", "put_item", "query", "transact_write_items")


def _marshal(data: dict[str, Any]) -> dict[str, Any]:
    """
    Python dict -> DynamoDB wire format.
    NB: floats are rejected - DynamoDB numbers are Decimal;
    our numeric fields are ints, which is fine.
    """
    return {k: _ser.serialize(v) for k, v in data.items()}


def _unmarshal(item: dict[str, Any]) -> dict[str, Any]:
    return {k: _de.deserialize(v) for k, v in item.items()}


def _check_client(client: Any) -> None:
    """
    Reject anything that cannot serve this repository's calls.

    A real botocore client can be identified exactly; anything else (a
    fake, a mock) only gets duck-typed on the methods we actually call.
    """
    missing = [
        name for name in _REQUIRED_CLIENT_METHODS
        if not callable(getattr(client, name, None))
    ]
    if missing:
        raise TypeError(
            f"client is missing {', '.join(missing)} - "
            f"expected a DynamoDB client, got {type(client).__name__}"
        )
    if not isinstance(client, BaseClient):
        return  # a test double; the duck-type check above is all we can do
    if not isinstance(client, AioBaseClient):
        # Sync clients have every method we need, so nothing complains
        # until `await <dict>` raises TypeError deep inside a request.
        raise TypeError(
            "client is a synchronous boto3 client; this repository awaits "
            "its calls. Use app.aws.aclients.open_async_client instead."
        )
    service = client.meta.service_model.service_name
    if service != "dynamodb":
        raise TypeError(f"client is for '{service}', expected 'dynamodb'")


def _check_table_name(table_name: str) -> None:
    if not isinstance(table_name, str):
        raise TypeError(
            f"table_name must be a str, got {type(table_name).__name__}"
        )
    if not _TABLE_NAME_RE.match(table_name):
        raise ValueError(
            f"invalid DynamoDB table name {table_name!r}: expected 3-255 "
            "characters from [A-Za-z0-9_.-]"
        )


def _error_code(exc: BaseException) -> str | None:
    """The AWS error code on a ClientError, if it carries one."""
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None
    return response.get("Error", {}).get("Code")


def _conflict_exception(client: Any) -> type[BaseException]:
    """
    Resolve TransactionCanceledException once, at construction.

    Reading it inside the `except` clause instead means a client that lacks
    the attribute raises AttributeError *while handling* the real error,
    masking it - and a MagicMock resolves it to a non-class, which makes
    `except` itself raise TypeError. Falling back to ClientError keeps the
    handler valid; update_status then filters on the error code.
    """
    exc = getattr(
        getattr(client, "exceptions", None), "TransactionCanceledException", None
    )
    if isinstance(exc, type) and issubclass(exc, BaseException):
        return exc
    return ClientError


class StatusConflictError(Exception):
    """
    The document was not in the expected status (a lost race, or an
    illegal transition). The transaction was cancelled; nothing changed.
    """


class DocumentRepository:

    def __init__(self, client: Any, table_name: str) -> None:
        """
        `client` must be an *async* DynamoDB client - see app.aws.aclients.
        Both arguments are checked here rather than trusted, because every
        way they can be wrong otherwise surfaces mid-request, as a 500 from
        a route that has no handler for it.
        """
        _check_client(client)
        _check_table_name(table_name)
        self._c = client
        self._table = table_name
        # Pinned now, not inside the except clause - see _conflict_exception.
        self._conflict_exc = _conflict_exception(client)
        self._conflict_is_typed = self._conflict_exc is not ClientError

    # - item shapes - - - - - - - - - - - - - - - - - - - - - - - - - -
    @staticmethod
    def _document_item(record: DocumentRecord) -> dict[str, Any]:
        return {
            "PK": f"DOC#{record.document_id}",
            "SK": "META",
            "entity_type": "document",
            "GSI1PK": f"OWNER#{record.owner}",
            # ISO-8601 UTC sorts lexicographically == chronologically;
            # the id suffix keeps ordering stable within one timestamp.
            "GSI1SK": (
                f"UPLOADED#{record.uploaded_at.isoformat()}"
                f"#{record.document_id}"
            ),
            **record.model_dump(mode="json", exclude_none=True),
        }

    # - pattern 1: get by id - - - - - - - - - - - - - - - - - - - - - -
    async def get(self, document_id: str) -> DocumentRecord | None:
        resp = await self._c.get_item(
            TableName=self._table,
            Key=_marshal({"PK": f"DOC#{document_id}", "SK": "META"}),
        )
        if "Item" not in resp:
            return None
        # Extra attributes (PK, SK, GSI1*, entity_type) are ignored by
        # pydantic; Decimals coerce back into the declared int fields.
        return DocumentRecord.model_validate(_unmarshal(resp["Item"]))

    # - create - - - - - - - - - - - - - - - - - - - - - - - - - - - - - 
    async def create(self, record: DocumentRecord) -> None:
        await self._c.put_item(
            TableName=self._table,
            Item=_marshal(self._document_item(record)),
            # A fresh UUID shouldn't collide, but the condition costs
            # nothing and makes an overwrite impossible rather than unlikely.
            ConditionExpression="attribute_not_exists(PK)",
        )

    # - pattern 2: list by owner, newest first (GSI1) - - - - - - - - - - 
    async def list_by_owner(
        self,
        owner: str,
        limit: int = 20,
        start_key: dict[str, Any] | None = None,
    ) -> tuple[list[DocumentRecord], dict[str, Any] | None]:
        kwargs: dict[str, Any] = {
            "TableName": self._table,
            "IndexName": "GSI1",
            "KeyConditionExpression": "GSI1PK = :pk",
            "ExpressionAttributeValues": _marshal({":pk": f"OWNER#{owner}"}),
            "ScanIndexForward": False, # descending sort key = newest first
            "Limit": limit,
        }
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key
        resp = await self._c.query(**kwargs)
        records = [DocumentRecord.model_validate(_unmarshal(i)) for i in resp["Items"]]
        return records, resp.get("LastEvaluatedKey")

    # - pattern 3: status history (one item collection, one query) - - - -
    async def history(self, document_id: str) -> list[StatusEvent]:
        resp = await self._c.query(
            TableName=self._table,
            KeyConditionExpression="PK = :pk AND begins_with(SK, :prefix)",
            ExpressionAttributeValues=_marshal(
                {":pk": f"DOC#{document_id}", ":prefix": "EVENT#"}
            ),
        )
        return [
            StatusEvent.model_validate(_unmarshal(i))
            for i in resp["Items"]
        ]

    # - pattern 4: the transactional status update - - - - - - - - - - - -
    async def update_status(
        self,
        document_id: str,
        to_status: DocumentStatus,
        expected: DocumentStatus,
        detail: str = "",
    ) -> None:
        """
        Move a document through the state machine, atomically writing
        the audit event with it. Raises StatusConflictError on a lost race
        or an illegal transition - in either case, nothing was written.
        """
        if to_status not in VALID_TRANSITIONS[expected]:
            raise StatusConflictError(
                f"illegal transition {expected} -> {to_status}"
            )
        now = utcnow()
        try:
            await self._c.transact_write_items(
                TransactItems=[
                    {
                        "Update": {
                            "TableName": self._table,
                            "Key": _marshal({
                                "PK": f"DOC#{document_id}",
                                "SK": "META"
                            }),
                            # 'status' is a DynamoDB reserved word, hence #s.
                            "UpdateExpression": (
                                "SET #s = :new, "
                                "updated_at = :now"
                            ),
                            "ConditionExpression": (
                                "attribute_exists(PK) "
                                "AND #s = :expected"
                            ),
                            "ExpressionAttributeNames": {"#s": "status"},
                            "ExpressionAttributeValues": _marshal({
                                ":new": to_status.value,
                                ":expected": expected.value,
                                ":now": now.isoformat(),
                            }),
                        }
                    }, {
                        "Put": {
                            "TableName": self._table,
                            "Item": _marshal({
                                "PK": f"DOC#{document_id}",
                                "SK": f"EVENT#{now.isoformat()}",
                                "entity_type": "status_event",
                                "document_id": document_id,
                                "occurred_at": now.isoformat(),
                                "from_status": expected.value,
                                "to_status": to_status.value,
                                "detail": detail,
                                # TTL attribute: epoch seconds.
                                "expires_at": int(
                                    (now + EVENT_TTL).timestamp()
                                ),
                            }),
                        }
                    },
                ]
            )
        except self._conflict_exc as exc:
            # On the ClientError fallback the class is far broader than the
            # one error we translate, so everything else keeps propagating.
            if not self._conflict_is_typed and _error_code(exc) != (
                "TransactionCanceledException"
            ):
                raise
            raise StatusConflictError(
                f"document {document_id} was not in status '{expected.value}'"
            ) from exc