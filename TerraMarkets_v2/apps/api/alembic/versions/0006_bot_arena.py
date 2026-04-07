"""add bot arena tables

Revision ID: 0006_bot_arena
Revises: 0005_data_fetch_requests
Create Date: 2026-03-23 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_bot_arena"
down_revision = "0005_data_fetch_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bot_status = sa.Enum("active", "paused", "archived", name="botstatus")
    bot_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bot_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("persona", sa.Text(), nullable=False, server_default=""),
        sa.Column("strategy_type", sa.String(length=64), nullable=False),
        sa.Column("status", bot_status, nullable=False, server_default="active"),
        sa.Column("cadence_minutes", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("bankroll_target", sa.Numeric(18, 6), nullable=False, server_default="1000"),
        sa.Column("max_trade_amount", sa.Numeric(18, 6), nullable=False, server_default="75"),
        sa.Column("max_market_exposure", sa.Numeric(18, 6), nullable=False, server_default="250"),
        sa.Column("config_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("tool_config_json", sa.JSON(), nullable=True),
        sa.Column("last_ran_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_bot_profiles_user_id", "bot_profiles", ["user_id"])
    op.create_index("ix_bot_profiles_strategy_type", "bot_profiles", ["strategy_type"])

    op.create_table(
        "bot_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bot_profile_id", sa.Integer(), sa.ForeignKey("bot_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("market_id", sa.Integer(), sa.ForeignKey("markets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trigger_source", sa.String(length=64), nullable=False, server_default="scheduled"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="running"),
        sa.Column("action_type", sa.String(length=32), nullable=False, server_default="hold"),
        sa.Column("outcome", sa.String(length=120), nullable=True),
        sa.Column("shares", sa.Numeric(18, 6), nullable=True),
        sa.Column("confidence", sa.Numeric(8, 6), nullable=True),
        sa.Column("thesis_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("citations_json", sa.JSON(), nullable=True),
        sa.Column("decision_payload_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_bot_runs_bot_profile_id", "bot_runs", ["bot_profile_id"])
    op.create_index("ix_bot_runs_market_id", "bot_runs", ["market_id"])


def downgrade() -> None:
    op.drop_index("ix_bot_runs_market_id", table_name="bot_runs")
    op.drop_index("ix_bot_runs_bot_profile_id", table_name="bot_runs")
    op.drop_table("bot_runs")
    op.drop_index("ix_bot_profiles_strategy_type", table_name="bot_profiles")
    op.drop_index("ix_bot_profiles_user_id", table_name="bot_profiles")
    op.drop_table("bot_profiles")
    sa.Enum(name="botstatus").drop(op.get_bind(), checkfirst=True)
