from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class PositionOut(BaseModel):
    market_id: int
    market_slug: str
    market_title: str
    market_status: str
    resolved_outcome: Optional[str] = None
    outcome: str
    shares: float
    current_price: Optional[float] = None
    cost_basis: float = 0.0
    current_value: Optional[float] = None
    unrealized_pl: Optional[float] = None
    settlement_value: Optional[float] = None
    realized_pl: Optional[float] = None


class OrderHistoryOut(BaseModel):
    order_id: int
    market_id: int
    market_slug: str
    market_title: str
    outcome: str
    shares: float
    cost: float
    avg_price: float
    created_at: str


class PortfolioOut(BaseModel):
    wallet_balance: float
    total_cost_basis: float
    total_current_value: float
    total_unrealized_pl: float
    settled_winnings: float
    open_positions: list[PositionOut]
    settled_positions: list[PositionOut]
    orders: list[OrderHistoryOut]
