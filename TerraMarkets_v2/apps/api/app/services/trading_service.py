from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import MarketStatus
from app.models.market import Market
from app.models.market_snapshot import MarketSnapshot
from app.models.order import Order
from app.models.position import Position
from app.models.wallet import LedgerEntry, Wallet
from app.services.lmsr import cost as lmsr_cost, implied_avg_price, prices as lmsr_prices, trade_cost_delta


def normalize_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_market_by_slug(db: Session, slug: str) -> Market:
    market = db.scalar(select(Market).where(Market.slug == slug))
    if not market:
        raise ValueError("Market not found.")
    return market


def execute_buy(db: Session, *, market: Market, user_id: int, outcome: str, shares: float) -> Order:
    if shares <= 0:
        raise ValueError("Shares must be positive.")

    close_at = normalize_utc(market.close_at)
    if close_at and close_at <= datetime.now(timezone.utc):
        market.status = MarketStatus.closed
    if market.status != MarketStatus.open:
        raise ValueError("Market is not open.")

    outcomes = list(market.outcomes)
    if outcome not in outcomes:
        raise ValueError("Invalid outcome.")

    q = dict(market.q or {})
    b = float(market.b)

    try:
        delta = float(trade_cost_delta(q, b, outcomes, outcome, shares))
        avg_price = float(implied_avg_price(q, b, outcomes, outcome, shares))
    except OverflowError as exc:
        raise ValueError("Order size is too large for this market.") from exc

    wallet = db.scalar(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    if wallet is None:
        raise ValueError("Wallet not found.")
    if float(wallet.balance) < delta:
        raise ValueError("Insufficient balance.")

    delta_decimal = Decimal(str(delta))
    shares_decimal = Decimal(str(shares))

    wallet.balance = Decimal(wallet.balance) - delta_decimal
    db.add(LedgerEntry(wallet_id=wallet.id, amount=-delta_decimal, memo=f"Buy {shares} {outcome} in {market.slug}"))

    q[outcome] = float(q.get(outcome, 0.0)) + float(shares)
    market.q = q

    order = Order(
        market_id=market.id,
        user_id=user_id,
        outcome=outcome,
        shares=shares,
        cost=delta,
        price=avg_price,
    )
    db.add(order)

    position = db.scalar(
        select(Position).where(
            Position.user_id == user_id,
            Position.market_id == market.id,
            Position.outcome == outcome,
        ).with_for_update()
    )
    if position is None:
        position = Position(user_id=user_id, market_id=market.id, outcome=outcome, shares=0)
        db.add(position)
        db.flush()
    position.shares = Decimal(position.shares) + shares_decimal

    record_market_snapshot(db, market=market, event_type="buy")

    return order


def market_prices(market: Market) -> dict:
    outcomes = list(market.outcomes)
    q = dict(market.q or {})
    return lmsr_prices(q, float(market.b), outcomes)


def resolve_and_settle(db: Session, *, market: Market, outcome: str) -> float:
    close_at = normalize_utc(market.close_at)
    if close_at and close_at <= datetime.now(timezone.utc) and market.status == MarketStatus.open:
        market.status = MarketStatus.closed

    if market.status not in {MarketStatus.open, MarketStatus.closed}:
        raise ValueError("Market cannot be resolved.")
    if outcome not in list(market.outcomes):
        raise ValueError("Invalid outcome.")

    market.status = MarketStatus.resolved
    market.resolved_outcome = outcome
    market.resolved_at = datetime.now(timezone.utc)

    total_paid = 0.0
    winners = db.scalars(select(Position).where(Position.market_id == market.id, Position.outcome == outcome)).all()
    for position in winners:
        win_amount = float(position.shares) * 1.0
        if win_amount <= 0:
            continue
        wallet = db.scalar(select(Wallet).where(Wallet.user_id == position.user_id).with_for_update())
        win_decimal = Decimal(str(win_amount))
        wallet.balance = Decimal(wallet.balance) + win_decimal
        db.add(LedgerEntry(wallet_id=wallet.id, amount=win_decimal, memo=f"Settlement win {market.slug}"))
        total_paid += win_amount

    record_market_snapshot(db, market=market, event_type="resolve")
    return total_paid


def record_market_snapshot(db: Session, *, market: Market, event_type: str) -> MarketSnapshot:
    q = {key: float(value) for key, value in (market.q or {}).items()}
    outcomes = list(market.outcomes)
    prices = lmsr_prices(q, float(market.b), outcomes)
    snapshot = MarketSnapshot(
        market_id=market.id,
        event_type=event_type,
        prices=prices,
        q=q,
        total_cost=Decimal(str(lmsr_cost(q, float(market.b), outcomes))),
    )
    db.add(snapshot)
    db.flush()
    return snapshot
