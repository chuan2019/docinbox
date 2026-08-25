"""
Domain models for docinbox documents.
The LLM-derived fields (summary, topics, entities, language,
doc_type) are declared now but stay empty until the Part 7
Lambda populates them.
"""
import enum
from datetime import datetime, timezone
from pydantic import BaseModel, Field

class DocumentStatus(str, enum.Enum):
    UPLOADED = "uploaded",
    PROCESSING = "processing",
    PROCESSED = "processed",
    FAILED = "failed"

# The status state machine. update_status() refuses anything
# not listed here, and the DynamoDB condition expression enforces
# it against races.
VALID_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.UPLOADED: {DocumentStatus.PROCESSING},
    DocumentStatus.PROCESSING: {DocumentStatus.PROCESSED, DocumentStatus.FAILED},
    DocumentStatus.PROCESSED: set(),
    DocumentStatus.FAILED: set(),
}

def utcnow() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class DocumentRecord(BaseModel):
    """
    One document's metadata - the app-facing shape, no DynamoDB keys.
    """
    document_id: str
    owner: str
    filename: str
    content_type: str
    size: int
    status: DocumentStatus = DocumentStatus.UPLOADED
    uploaded_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    # - - LLM-derived fields, written by the Part 7 Lambda - -
    summary: str | None = None
    topics: list[str] | None = None
    entities: list[str] | None = None
    language: str | None = None
    doc_type: str | None = None


class StatusEvent(BaseModel):
    """
    One entry in a document's status history (a TTL'd audit record).
    """
    document_id: str
    occurred_at: datetime = Field(default_factory=utcnow)
    from_status: DocumentStatus
    to_status: DocumentStatus
    detail: str = ""
