from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)


class AppSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "app_settings"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    default_llm_provider: Mapped[str] = mapped_column(String(80), nullable=False)
    default_deep_model: Mapped[str] = mapped_column(String(160), nullable=False)
    default_quick_model: Mapped[str] = mapped_column(String(160), nullable=False)
    default_output_language: Mapped[str] = mapped_column(String(80), nullable=False)
    default_analysts: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    default_research_depth: Mapped[int] = mapped_column(Integer, nullable=False)
    default_checkpoint_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    deepseek_api_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    fred_api_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    user: Mapped[User] = relationship()


class Run(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "runs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(40), nullable=False)
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    status_reason: Mapped[str | None] = mapped_column(Text)
    config_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    selected_analysts: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    checkpoint_thread_id: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    interrupted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship()


class RunEvent(Base):
    __tablename__ = "run_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    agent_name: Mapped[str | None] = mapped_column(String(120))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[Run] = relationship()


class RunReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "run_reports"

    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    section: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    run: Mapped[Run] = relationship()


class RunMetric(Base):
    __tablename__ = "run_metrics"

    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), primary_key=True)
    llm_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tool_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    elapsed_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analyst_wall_times: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run: Mapped[Run] = relationship()


class RagDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rag_documents"

    source_id: Mapped[str] = mapped_column(String(240), unique=True, nullable=False)
    ticker: Mapped[str] = mapped_column(String(40), nullable=False)
    scope: Mapped[str] = mapped_column(String(80), nullable=False)
    source_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_name: Mapped[str] = mapped_column(String(240), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    published_at: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[date | None] = mapped_column(Date)
    url: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    confidence: Mapped[str] = mapped_column(String(40), nullable=False)
    license_note: Mapped[str] = mapped_column(String(120), nullable=False)
    # 中文注释：metadata 是 SQLAlchemy 保留名，Python 属性避开但数据库列仍叫 metadata。
    document_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # 中文注释：RAG source 停用只影响后续检索，历史 evidence/chunk 仍保留。
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(String(120))


class RagChunk(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rag_chunks"

    document_id: Mapped[str] = mapped_column(ForeignKey("rag_documents.id"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    document: Mapped[RagDocument] = relationship()


class RunEvidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "run_evidence"

    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"), nullable=False)
    chunk_id: Mapped[str] = mapped_column(ForeignKey("rag_chunks.id"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(120), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    citation_key: Mapped[str | None] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float, nullable=False)
    excerpt: Mapped[str] = mapped_column(Text, nullable=False)

    run: Mapped[Run] = relationship()
    chunk: Mapped[RagChunk] = relationship()
