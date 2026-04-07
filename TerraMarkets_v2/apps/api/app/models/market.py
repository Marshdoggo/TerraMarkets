from __future__ import annotations

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import MarketStatus


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(120), index=True, nullable=False, default="climate")
    description: Mapped[str] = mapped_column(String(2000), nullable=True)
    resolution_criteria: Mapped[str] = mapped_column(Text, nullable=False, default="")
    close_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[MarketStatus] = mapped_column(Enum(MarketStatus), default=MarketStatus.open, nullable=False)
    outcomes: Mapped[dict] = mapped_column(JSON, nullable=False)
    b: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=50)
    q: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    resolved_outcome: Mapped[str] = mapped_column(String(120), nullable=True)
    resolved_at: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    orders = relationship("Order", back_populates="market", cascade="all, delete-orphan")
