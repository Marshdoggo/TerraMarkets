"""repair missing auxiliary tables

Revision ID: 0004_repair_missing_aux_tables
Revises: 0003_market_metadata
Create Date: 2026-03-15

"""

from alembic import op
import sqlalchemy as sa

revision = "0004_repair_missing_aux_tables"
down_revision = "0003_market_metadata"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "market_data_links" not in tables:
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

    if "purchase_requests" not in tables:
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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "purchase_requests" in tables:
        op.drop_index("ix_purchase_requests_user_id", table_name="purchase_requests")
        op.drop_table("purchase_requests")

    if "market_data_links" in tables:
        op.drop_index("ix_market_data_links_market_id", table_name="market_data_links")
        op.drop_table("market_data_links")
