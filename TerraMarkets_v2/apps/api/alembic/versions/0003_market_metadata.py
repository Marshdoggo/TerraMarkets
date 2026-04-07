"""market metadata

Revision ID: 0003_market_metadata
Revises: 0002_market_snapshots_and_data
Create Date: 2026-03-10

"""

from alembic import op
import sqlalchemy as sa

revision = "0003_market_metadata"
down_revision = "0002_market_snapshots_and_data"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("markets", sa.Column("category", sa.String(length=120), nullable=True))
    op.add_column("markets", sa.Column("resolution_criteria", sa.Text(), nullable=True))
    op.add_column("markets", sa.Column("close_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_markets_category", "markets", ["category"], unique=False)
    op.execute("UPDATE markets SET category='climate indicators' WHERE category IS NULL")
    op.execute("UPDATE markets SET resolution_criteria='Admin resolution criteria to be backfilled.' WHERE resolution_criteria IS NULL")
    op.execute("UPDATE markets SET close_at=CURRENT_TIMESTAMP WHERE close_at IS NULL")
    with op.batch_alter_table("markets") as batch_op:
        batch_op.alter_column("category", existing_type=sa.String(length=120), nullable=False)
        batch_op.alter_column("resolution_criteria", existing_type=sa.Text(), nullable=False)
        batch_op.alter_column("close_at", existing_type=sa.DateTime(timezone=True), nullable=False)


def downgrade():
    op.drop_index("ix_markets_category", table_name="markets")
    with op.batch_alter_table("markets") as batch_op:
        batch_op.drop_column("close_at")
        batch_op.drop_column("resolution_criteria")
        batch_op.drop_column("category")
