"""
DocumentRepository - every DynamoDB key decision in the app lives here.

Key design (the whole single-table layout, in one place):

    document:       PK=DOC#<id> SK=META             GSI1PK=OWNER#<owner>
                                                    GSI1SK=UPLOADED#<iso-ts>#<id>
    status event:   PK=DOC#<id> SK=EVENT#<iso-ts>   (no GSI keys - sparse)
"""
from datetime import timedelta
from typing import Any

from boto3.dynamodb.types import TypeDeserializer, TypeSerializer

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


def _marshal(data: dict[str, Any]) -> dict[str, Any]:
    """
    Python dict -> DynamoDB wire format.
    NB: floats are rejected - DynamoDB numbers are Decimal;
    our numeric fields are ints, which is fine.
    """
    return {k: _ser.serialize(v) for k, v in data.items()}


def _unmarshal(item: dict[str, Any]) -> dict[str, Any]:
    return {k: _de.deserialize(v) for k, v in item.items()}


class StatusConflictError(Exception):
    """
    The document was not in the expected status (a lost race, or an
    illegal transition). The transaction was cancelled; nothing changed.
    """


class DocumentRepository:

    def __init__(self, client: Any, table_name: str) -> None:
        self._c = client
        self._table = table_name

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
        except self._c.exceptions.TransactionCanceledException as exc:
            raise StatusConflictError(
                f"document {document_id} was not in status '{expected.value}'"
            ) from exc