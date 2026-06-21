"""add run evidence citation key

Revision ID: 0004_rag_evidence_citations
Revises: 0003_add_rag_tables
Create Date: 2026-06-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_rag_evidence_citations"
down_revision: str | None = "0003_add_rag_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("run_evidence", sa.Column("citation_key", sa.String(length=32), nullable=True))
    op.create_index(
        "uq_run_evidence_run_citation_key",
        "run_evidence",
        ["run_id", "citation_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_run_evidence_run_citation_key", table_name="run_evidence")
    op.drop_column("run_evidence", "citation_key")
