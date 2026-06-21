"""add rag tables

Revision ID: 0003_add_rag_tables
Revises: 0002_add_settings_api_keys
Create Date: 2026-06-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_add_rag_tables"
down_revision: str | None = "0002_add_settings_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rag_documents",
        sa.Column("source_id", sa.String(length=240), nullable=False),
        sa.Column("ticker", sa.String(length=40), nullable=False),
        sa.Column("scope", sa.String(length=80), nullable=False),
        sa.Column("source_type", sa.String(length=120), nullable=False),
        sa.Column("source_name", sa.String(length=240), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.Date(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("confidence", sa.String(length=40), nullable=False),
        sa.Column("license_note", sa.String(length=120), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id"),
    )
    op.create_index("idx_rag_documents_ticker_scope", "rag_documents", ["ticker", "scope"])
    op.create_index("idx_rag_documents_source_type", "rag_documents", ["source_type"])

    op.create_table(
        "rag_chunks",
        sa.Column("document_id", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["rag_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_rag_chunks_doc_index", "rag_chunks", ["document_id", "chunk_index"], unique=True)

    op.create_table(
        "run_evidence",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("chunk_id", sa.String(), nullable=False),
        sa.Column("agent_name", sa.String(length=120), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["chunk_id"], ["rag_chunks.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_run_evidence_run_id", "run_evidence", ["run_id"])
    op.create_index("idx_run_evidence_agent", "run_evidence", ["run_id", "agent_name"])


def downgrade() -> None:
    op.drop_index("idx_run_evidence_agent", table_name="run_evidence")
    op.drop_index("idx_run_evidence_run_id", table_name="run_evidence")
    op.drop_table("run_evidence")
    op.drop_index("uq_rag_chunks_doc_index", table_name="rag_chunks")
    op.drop_table("rag_chunks")
    op.drop_index("idx_rag_documents_source_type", table_name="rag_documents")
    op.drop_index("idx_rag_documents_ticker_scope", table_name="rag_documents")
    op.drop_table("rag_documents")
