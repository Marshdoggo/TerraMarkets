from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    outcome: Mapped[str] = mapped_column(String(120), nullable=False)
    shares: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    cost: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    market = relationship("Market", back_populates="orders")

