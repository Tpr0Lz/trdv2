"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "app_settings",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("default_llm_provider", sa.String(length=80), nullable=False),
        sa.Column("default_deep_model", sa.String(length=160), nullable=False),
        sa.Column("default_quick_model", sa.String(length=160), nullable=False),
        sa.Column("default_output_language", sa.String(length=80), nullable=False),
        sa.Column("default_analysts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("default_research_depth", sa.Integer(), nullable=False),
        sa.Column("default_checkpoint_enabled", sa.Boolean(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "runs",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("ticker", sa.String(length=40), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("asset_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("status_reason", sa.Text(), nullable=True),
        sa.Column("config_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("selected_analysts", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checkpoint_thread_id", sa.String(length=120), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interrupted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checkpoint_thread_id"),
    )
    op.create_index("idx_runs_status", "runs", ["status"])
    op.create_index("idx_runs_ticker_date", "runs", ["ticker", "analysis_date"])
    op.create_index("idx_runs_user_created", "runs", ["user_id", "created_at"])
    op.create_table(
        "run_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("agent_name", sa.String(length=120), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_run_events_run_id_id", "run_events", ["run_id", "id"])
    op.create_index("uq_run_events_sequence", "run_events", ["run_id", "sequence"], unique=True)
    op.create_table(
        "run_metrics",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("llm_calls", sa.Integer(), nullable=False),
        sa.Column("tool_calls", sa.Integer(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=False),
        sa.Column("analyst_wall_times", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_table(
        "run_reports",
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("section", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("uq_run_reports_section", "run_reports", ["run_id", "section"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_run_reports_section", table_name="run_reports")
    op.drop_table("run_reports")
    op.drop_table("run_metrics")
    op.drop_index("uq_run_events_sequence", table_name="run_events")
    op.drop_index("idx_run_events_run_id_id", table_name="run_events")
    op.drop_table("run_events")
    op.drop_index("idx_runs_user_created", table_name="runs")
    op.drop_index("idx_runs_ticker_date", table_name="runs")
    op.drop_index("idx_runs_status", table_name="runs")
    op.drop_table("runs")
    op.drop_table("app_settings")
    op.drop_table("users")

