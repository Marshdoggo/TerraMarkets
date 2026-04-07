from __future__ import annotations

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import BotStatus


class BotProfile(Base):
    __tablename__ = "bot_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    persona: Mapped[str] = mapped_column(Text, nullable=False, default="")
    strategy_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    status: Mapped[BotStatus] = mapped_column(Enum(BotStatus), nullable=False, default=BotStatus.active)
    cadence_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    bankroll_target: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=1000)
    max_trade_amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=75)
    max_market_exposure: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=250)
    config_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    tool_config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_ran_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="bot_profile")
    runs = relationship("BotRun", back_populates="bot_profile", cascade="all, delete-orphan")


class BotRun(Base):
    __tablename__ = "bot_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bot_profile_id: Mapped[int] = mapped_column(ForeignKey("bot_profiles.id", ondelete="CASCADE"), index=True, nullable=False)
    market_id: Mapped[int | None] = mapped_column(ForeignKey("markets.id", ondelete="SET NULL"), index=True, nullable=True)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    trigger_source: Mapped[str] = mapped_column(String(64), nullable=False, default="scheduled")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, default="hold")
    outcome: Mapped[str | None] = mapped_column(String(120), nullable=True)
    shares: Mapped[float | None] = mapped_column(Numeric(18, 6), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(8, 6), nullable=True)
    thesis_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    decision_payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)

    bot_profile = relationship("BotProfile", back_populates="runs")
    market = relationship("Market")
    order = relationship("Order")
