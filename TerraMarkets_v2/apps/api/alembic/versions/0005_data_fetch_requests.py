"""add data fetch requests

Revision ID: 0005_data_fetch_requests
Revises: 0004_repair_missing_aux_tables
Create Date: 2026-03-19 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_data_fetch_requests"
down_revision = "0004_repair_missing_aux_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_fetch_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("requested_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_data_fetch_requests_source_key", "data_fetch_requests", ["source_key"])
    op.create_index("ix_data_fetch_requests_requested_by_user_id", "data_fetch_requests", ["requested_by_user_id"])
    op.create_index("ix_data_fetch_requests_reviewed_by_user_id", "data_fetch_requests", ["reviewed_by_user_id"])


def downgrade() -> None:
    op.drop_index("ix_data_fetch_requests_reviewed_by_user_id", table_name="data_fetch_requests")
    op.drop_index("ix_data_fetch_requests_requested_by_user_id", table_name="data_fetch_requests")
    op.drop_index("ix_data_fetch_requests_source_key", table_name="data_fetch_requests")
    op.drop_table("data_fetch_requests")
