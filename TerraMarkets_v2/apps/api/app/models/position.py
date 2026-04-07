from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("user_id", "market_id", "outcome", name="uq_position"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    market_id: Mapped[int] = mapped_column(ForeignKey("markets.id", ondelete="CASCADE"), index=True, nullable=False)
    outcome: Mapped[str] = mapped_column(String(120), nullable=False)
    shares: Mapped[float] = mapped_column(Numeric(18, 6), default=0, nullable=False)

