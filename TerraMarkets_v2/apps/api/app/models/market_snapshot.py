from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    prices: Mapped[dict] = mapped_column(JSON, nullable=False)
    q: Mapped[dict] = mapped_column(JSON, nullable=False)
    total_cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

