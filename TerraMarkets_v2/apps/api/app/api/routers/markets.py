from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_tier
from app.core.db import get_db
from app.models.bot import BotProfile, BotRun
from app.models.enums import UserTier
from app.models.market_data_link import MarketDataLink
from app.models.market import Market
from app.models.market_snapshot import MarketSnapshot
from app.models.user import User
from app.schemas.market import (
    BotCommentaryOut,
    DemoSeedSummaryOut,
    MarketCreateIn,
    MarketDataLinkIn,
    MarketDataLinkOut,
    MarketDetailOut,
    LinkedSeriesPointOut,
    MarketOut,
    MarketSnapshotOut,
    ResolveIn,
    SettlementOut,
    TradeIn,
    TradeOut,
)
from app.services.bot_service import serialize_run
from app.services.demo_market_service import seed_demo_markets
from app.services.trading_service import execute_buy, get_market_by_slug, market_prices, record_market_snapshot, resolve_and_settle
from app.services.data_service import get_latest_point_for_series, list_recent_points_for_series

router = APIRouter(prefix="/markets", tags=["markets"])


def serialize_market(market: Market) -> MarketOut:
    return MarketOut(
        id=market.id,
        slug=market.slug,
        title=market.title,
        category=market.category,
        description=market.description,
        resolution_criteria=market.resolution_criteria,
        close_at=str(market.close_at),
        status=market.status.value,
        outcomes=list(market.outcomes),
        b=float(market.b),
        q={key: float(value) for key, value in (market.q or {}).items()},
        prices=market_prices(market),
        resolved_outcome=market.resolved_outcome,
    )


def serialize_snapshot(snapshot: MarketSnapshot) -> MarketSnapshotOut:
    return MarketSnapshotOut(
        id=snapshot.id,
        event_type=snapshot.event_type,
        prices={key: float(value) for key, value in (snapshot.prices or {}).items()},
        q={key: float(value) for key, value in (snapshot.q or {}).items()},
        total_cost=float(snapshot.total_cost),
        created_at=str(snapshot.created_at),
    )


def serialize_link(link: MarketDataLink, latest_point=None, recent_points=None) -> MarketDataLinkOut:
    return MarketDataLinkOut(
        id=link.id,
        source_key=link.source_key,
        series_key=link.series_key,
        label=link.label,
        notes=link.notes,
        latest_numeric_value=float(latest_point.numeric_value) if latest_point and latest_point.numeric_value is not None else None,
        latest_unit=latest_point.unit if latest_point else None,
        latest_observed_at=str(latest_point.observed_at) if latest_point else None,
        recent_points=[
            LinkedSeriesPointOut(
                observed_at=str(point.observed_at),
                numeric_value=float(point.numeric_value) if point.numeric_value is not None else None,
            )
            for point in (recent_points or [])
        ],
    )


@router.post("", response_model=MarketOut)
def create_market(
    payload: MarketCreateIn,
    admin: User = Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    outcomes = [outcome.strip() for outcome in payload.outcomes]
    if len(set(outcomes)) != len(outcomes):
        raise HTTPException(status_code=400, detail="Duplicate outcomes.")

    market = Market(
        slug=payload.slug.strip(),
        title=payload.title.strip(),
        category=payload.category.strip(),
        description=payload.description,
        resolution_criteria=payload.resolution_criteria.strip(),
        close_at=payload.close_at,
        outcomes=outcomes,
        b=payload.b,
        q={outcome: 0.0 for outcome in outcomes},
        created_by_user_id=admin.id,
    )
    db.add(market)
    db.commit()
    db.refresh(market)
    record_market_snapshot(db, market=market, event_type="create")
    db.commit()
    return serialize_market(market)


@router.post("/seed/demo", response_model=DemoSeedSummaryOut)
def seed_demo_market_catalog(
    admin: User = Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    summary = seed_demo_markets(db)
    db.commit()
    return DemoSeedSummaryOut(**summary)


@router.get("", response_model=list[MarketOut])
def list_markets(db: Session = Depends(get_db)):
    markets = db.scalars(select(Market).order_by(Market.id.desc()).limit(100)).all()
    return [serialize_market(market) for market in markets]


@router.get("/{slug}", response_model=MarketDetailOut)
def get_market(slug: str, db: Session = Depends(get_db)):
    market = get_market_by_slug(db, slug)
    snapshots = db.scalars(select(MarketSnapshot).where(MarketSnapshot.market_id == market.id).order_by(MarketSnapshot.id.desc()).limit(100)).all()
    links = db.scalars(select(MarketDataLink).where(MarketDataLink.market_id == market.id).order_by(MarketDataLink.id.desc())).all()
    unique_links = []
    seen_keys = set()
    for link in links:
        dedupe_key = (link.source_key, link.series_key)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        unique_links.append(link)
    payload = serialize_market(market).model_dump()
    payload["snapshots"] = [serialize_snapshot(snapshot) for snapshot in snapshots]
    payload["data_links"] = [
        serialize_link(
            link,
            latest_point=get_latest_point_for_series(db, source_key=link.source_key, series_key=link.series_key),
            recent_points=list_recent_points_for_series(
                db, source_key=link.source_key, series_key=link.series_key, limit=400
            ),
        )
        for link in unique_links
    ]
    return MarketDetailOut(**payload)


@router.get("/{slug}/bot-commentary", response_model=list[BotCommentaryOut])
def get_market_bot_commentary(slug: str, db: Session = Depends(get_db)):
    market = get_market_by_slug(db, slug)
    runs = db.scalars(
        select(BotRun)
        .join(BotProfile, BotRun.bot_profile_id == BotProfile.id)
        .where(
            BotRun.market_id == market.id,
            BotRun.status == "completed",
            BotRun.thesis_summary.is_not(None),
        )
        .order_by(BotRun.id.desc())
        .limit(25)
    ).all()
    return [
        BotCommentaryOut(
            id=run.id,
            market_slug=market.slug,
            bot_profile_id=run.bot_profile_id,
            bot_display_name=run.bot_profile.display_name,
            bot_persona=run.bot_profile.persona,
            strategy_type=run.bot_profile.strategy_type,
            action_type=run.action_type,
            outcome=run.outcome,
            shares=float(run.shares) if run.shares is not None else None,
            confidence=float(run.confidence) if run.confidence is not None else None,
            thesis_summary=run.thesis_summary,
            citations=serialize_run(run)["citations"],
            created_at=str(run.finished_at or run.started_at),
        )
        for run in runs
    ]


@router.post("/{slug}/buy", response_model=TradeOut)
def buy(slug: str, payload: TradeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        market = get_market_by_slug(db, slug)
        order = execute_buy(db, market=market, user_id=user.id, outcome=payload.outcome, shares=payload.shares)
        db.commit()
        db.refresh(order)
        return TradeOut(
            order_id=order.id,
            cost=float(order.cost),
            avg_price=float(order.price),
            new_prices=market_prices(market),
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{slug}/resolve", response_model=SettlementOut)
def resolve(
    slug: str,
    payload: ResolveIn,
    admin: User = Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    try:
        market = get_market_by_slug(db, slug)
        total_paid = resolve_and_settle(db, market=market, outcome=payload.outcome)
        db.commit()
        return SettlementOut(market_id=market.id, outcome=payload.outcome, total_paid=float(total_paid))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{slug}/links", response_model=MarketDataLinkOut)
def create_market_link(
    slug: str,
    payload: MarketDataLinkIn,
    admin: User = Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    market = get_market_by_slug(db, slug)
    existing = db.scalar(
        select(MarketDataLink).where(
            MarketDataLink.market_id == market.id,
            MarketDataLink.source_key == payload.source_key,
            MarketDataLink.series_key == payload.series_key,
        )
    )
    if existing:
        return serialize_link(
            existing,
            latest_point=get_latest_point_for_series(db, source_key=existing.source_key, series_key=existing.series_key),
            recent_points=list_recent_points_for_series(
                db, source_key=existing.source_key, series_key=existing.series_key, limit=400
            ),
        )
    link = MarketDataLink(
        market_id=market.id,
        source_key=payload.source_key,
        series_key=payload.series_key,
        label=payload.label,
        notes=payload.notes,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return serialize_link(link)
