"""add settings api keys

Revision ID: 0002_add_settings_api_keys
Revises: 0001_initial_schema
Create Date: 2026-06-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_add_settings_api_keys"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_settings",
        sa.Column("deepseek_api_key", sa.String(length=512), nullable=False, server_default=""),
    )
    op.add_column(
        "app_settings",
        sa.Column("fred_api_key", sa.String(length=512), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("app_settings", "fred_api_key")
    op.drop_column("app_settings", "deepseek_api_key")
