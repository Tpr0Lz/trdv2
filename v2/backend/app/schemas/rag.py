from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class RagEvidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    agent_name: str
    query: str
    citation_key: str | None
    score: float
    excerpt: str
    source_id: str
    source_title: str
    source_type: str
    source_name: str
    published_at: date | None
    url: str | None
    created_at: datetime


class RunEvidenceResponse(BaseModel):
    items: list[RagEvidenceItem]


class RagSourceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    ticker: str
    scope: str
    source_type: str
    source_name: str
    title: str
    published_at: date | None
    retrieved_at: date | None
    confidence: str
    license_note: str
    is_deleted: bool
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RagSourcesResponse(BaseModel):
    items: list[RagSourceItem]


class RagImportResponse(BaseModel):
    documents_imported: int
    chunks_imported: int


class RagDeleteResponse(BaseModel):
    source_id: str
    deleted: bool


class RagRestoreResponse(BaseModel):
    source_id: str
    restored: bool


class RetrievedEvidence(BaseModel):
    chunk_id: str
    citation_key: str | None
    agent_name: str
    query: str
    score: float
    excerpt: str
    source_id: str
    source_title: str
    source_type: str
    source_name: str
    published_at: date | None
    url: str | None
