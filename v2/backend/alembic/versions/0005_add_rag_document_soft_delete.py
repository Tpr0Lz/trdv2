"""add rag document soft delete

Revision ID: 0005_rag_document_soft_delete
Revises: 0004_rag_evidence_citations
Create Date: 2026-06-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_rag_document_soft_delete"
down_revision: str | None = "0004_rag_evidence_citations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rag_documents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rag_documents", sa.Column("deleted_by", sa.String(length=120), nullable=True))
    op.create_index("idx_rag_documents_deleted_at", "rag_documents", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("idx_rag_documents_deleted_at", table_name="rag_documents")
    op.drop_column("rag_documents", "deleted_by")
    op.drop_column("rag_documents", "deleted_at")
