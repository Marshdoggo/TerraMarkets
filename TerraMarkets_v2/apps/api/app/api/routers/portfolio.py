from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.market import Market
from app.models.order import Order
from app.models.position import Position
from app.models.user import User
from app.models.wallet import LedgerEntry, Wallet
from app.schemas.portfolio import OrderHistoryOut, PortfolioOut, PositionOut

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioOut)
def get_portfolio(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user.id))
    positions = db.scalars(select(Position).where(Position.user_id == user.id).order_by(Position.id.desc())).all()
    orders = db.scalars(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())).all()

    markets = {
        market.id: market
        for market in db.scalars(select(Market).where(Market.id.in_({position.market_id for position in positions} | {order.market_id for order in orders}))).all()
    }

    open_positions = []
    settled_positions = []
    total_cost_basis = 0.0
    total_current_value = 0.0
    for position in positions:
        market = markets.get(position.market_id)
        current_price = None
        current_value = None
        cost_basis = 0.0
        settlement_value = None
        realized_pl = None
        if market and market.q and position.outcome in market.q:
            from app.services.trading_service import market_prices

            current_price = market_prices(market).get(position.outcome)
            current_value = float(position.shares) * float(current_price)
        for order in orders:
            if order.market_id == position.market_id and order.outcome == position.outcome:
                cost_basis += float(order.cost)

        if market and market.status.value == "resolved":
            settlement_value = float(position.shares) if market.resolved_outcome == position.outcome else 0.0
            realized_pl = settlement_value - cost_basis

        total_cost_basis += cost_basis
        total_current_value += current_value or 0.0
        position_out = PositionOut(
            market_id=position.market_id,
            market_slug=market.slug if market else "",
            market_title=market.title if market else "",
            market_status=market.status.value if market else "unknown",
            resolved_outcome=market.resolved_outcome if market else None,
            outcome=position.outcome,
            shares=float(position.shares),
            current_price=float(current_price) if current_price is not None else None,
            cost_basis=cost_basis,
            current_value=current_value,
            unrealized_pl=(current_value - cost_basis) if current_value is not None else None,
            settlement_value=settlement_value,
            realized_pl=realized_pl,
        )
        if market and market.status.value == "resolved":
            settled_positions.append(position_out)
        else:
            open_positions.append(position_out)

    serialized_orders = []
    for order in orders:
        market = markets.get(order.market_id)
        serialized_orders.append(
            OrderHistoryOut(
                order_id=order.id,
                market_id=order.market_id,
                market_slug=market.slug if market else "",
                market_title=market.title if market else "",
                outcome=order.outcome,
                shares=float(order.shares),
                cost=float(order.cost),
                avg_price=float(order.price),
                created_at=str(order.created_at),
            )
        )

    settled_winnings = 0.0
    if wallet:
        entries = db.scalars(select(LedgerEntry).where(LedgerEntry.wallet_id == wallet.id)).all()
        for entry in entries:
            if entry.memo.startswith("Settlement win"):
                settled_winnings += float(entry.amount)

    return PortfolioOut(
        wallet_balance=float(wallet.balance) if wallet else 0.0,
        total_cost_basis=total_cost_basis,
        total_current_value=total_current_value,
        total_unrealized_pl=total_current_value - total_cost_basis,
        settled_winnings=settled_winnings,
        open_positions=open_positions,
        settled_positions=settled_positions,
        orders=serialized_orders,
    )
