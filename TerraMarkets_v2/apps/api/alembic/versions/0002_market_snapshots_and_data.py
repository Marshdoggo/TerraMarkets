"""market snapshots and data runs

Revision ID: 0002_market_snapshots_and_data
Revises: 0001_init
Create Date: 2026-03-09

"""

from alembic import op
import sqlalchemy as sa

revision = "0002_market_snapshots_and_data"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("prices", sa.JSON(), nullable=False),
        sa.Column("q", sa.JSON(), nullable=False),
        sa.Column("total_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_market_snapshots_market_id", "market_snapshots", ["market_id"], unique=False)

    op.create_table(
        "data_source_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_data_source_runs_source_key", "data_source_runs", ["source_key"], unique=False)

    op.create_table(
        "data_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_run_id", sa.Integer(), sa.ForeignKey("data_source_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("series_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("numeric_value", sa.Numeric(18, 6), nullable=True),
        sa.Column("unit", sa.String(length=64), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_data_points_source_run_id", "data_points", ["source_run_id"], unique=False)
    op.create_index("ix_data_points_source_key", "data_points", ["source_key"], unique=False)
    op.create_index("ix_data_points_series_key", "data_points", ["series_key"], unique=False)

    op.create_table(
        "market_data_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("series_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_market_data_links_market_id", "market_data_links", ["market_id"], unique=False)

    op.create_table(
        "purchase_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(18, 6), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_purchase_requests_user_id", "purchase_requests", ["user_id"], unique=False)

def downgrade():
    op.drop_index("ix_purchase_requests_user_id", table_name="purchase_requests")
    op.drop_table("purchase_requests")

    op.drop_index("ix_market_data_links_market_id", table_name="market_data_links")
    op.drop_table("market_data_links")

    op.drop_index("ix_data_points_series_key", table_name="data_points")
    op.drop_index("ix_data_points_source_key", table_name="data_points")
    op.drop_index("ix_data_points_source_run_id", table_name="data_points")
    op.drop_table("data_points")

    op.drop_index("ix_data_source_runs_source_key", table_name="data_source_runs")
    op.drop_table("data_source_runs")

    op.drop_index("ix_market_snapshots_market_id", table_name="market_snapshots")
    op.drop_table("market_snapshots")
