from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_tier
from app.core.db import get_db
from app.models.bot import BotProfile, BotRun
from app.models.market import Market
from app.models.enums import BotStatus, UserTier
from app.models.order import Order
from app.models.position import Position
from app.models.wallet import Wallet
from app.schemas.bot import (
    ArenaSeedOut,
    BotCycleRunIn,
    BotLeaderboardOut,
    BotProfileCreateIn,
    BotProfileOut,
    BotProfileUpdateIn,
    BotRunOut,
    BotSchedulerStatusOut,
    BotThesisFeedOut,
    PublicBotPositionOut,
    PublicBotProfileOut,
    PublicBotRunOut,
)
from app.services.bot_service import create_bot_profile, reset_arena_state, run_bot_for_market, run_cycle, scheduler, seed_default_bots, serialize_profile, serialize_run
from app.services.trading_service import get_market_by_slug, market_prices

router = APIRouter(prefix="/bots", tags=["bots"])


def _serialize_public_run(run: BotRun) -> PublicBotRunOut:
    return PublicBotRunOut(
        id=run.id,
        bot_profile_id=run.bot_profile_id,
        bot_display_name=run.bot_profile.display_name if run.bot_profile else None,
        bot_persona=run.bot_profile.persona if run.bot_profile else None,
        strategy_type=run.bot_profile.strategy_type if run.bot_profile else None,
        market_id=run.market_id,
        market_slug=run.market.slug if run.market else None,
        market_title=run.market.title if run.market else None,
        trigger_source=run.trigger_source,
        action_type=run.action_type,
        outcome=run.outcome,
        shares=float(run.shares) if run.shares is not None else None,
        confidence=float(run.confidence) if run.confidence is not None else None,
        thesis_summary=run.thesis_summary,
        citations=serialize_run(run)["citations"],
        started_at=str(run.started_at),
        finished_at=str(run.finished_at) if run.finished_at else None,
    )


def _serialize_public_bot(db: Session, bot: BotProfile, include_detail: bool = False) -> PublicBotProfileOut:
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == bot.user_id))
    positions = db.scalars(select(Position).where(Position.user_id == bot.user_id).order_by(Position.id.desc())).all()
    orders = db.scalars(select(Order).where(Order.user_id == bot.user_id).order_by(Order.id.desc())).all()
    runs = db.scalars(select(BotRun).where(BotRun.bot_profile_id == bot.id).order_by(BotRun.id.desc()).limit(25 if include_detail else 5)).all()
    all_runs = db.scalars(select(BotRun).where(BotRun.bot_profile_id == bot.id)).all()
    market_ids = {position.market_id for position in positions} | {order.market_id for order in orders} | {run.market_id for run in runs if run.market_id}
    markets = {market.id: market for market in db.scalars(select(Market).where(Market.id.in_(market_ids))).all()} if market_ids else {}

    cost_basis_by_key: dict[tuple[int, str], float] = {}
    for order in orders:
        cost_basis_by_key.setdefault((order.market_id, order.outcome), 0.0)
        cost_basis_by_key[(order.market_id, order.outcome)] += float(order.cost)

    open_positions: list[PublicBotPositionOut] = []
    settled_positions: list[PublicBotPositionOut] = []
    total_cost_basis = 0.0
    open_cost_basis = 0.0
    open_value = 0.0
    realized_pl = 0.0
    for position in positions:
        market = markets.get(position.market_id)
        cost_basis = cost_basis_by_key.get((position.market_id, position.outcome), 0.0)
        current_value = None
        unrealized_pl = None
        position_realized_pl = None
        if market and market.status.value == "resolved":
            settlement_value = float(position.shares) if market.resolved_outcome == position.outcome else 0.0
            position_realized_pl = settlement_value - cost_basis
            realized_pl += position_realized_pl
        elif market:
            current_price = market_prices(market).get(position.outcome)
            current_value = float(position.shares) * float(current_price) if current_price is not None else None
            unrealized_pl = current_value - cost_basis if current_value is not None else None
            open_value += current_value or 0.0
            open_cost_basis += cost_basis
        total_cost_basis += cost_basis
        payload = PublicBotPositionOut(
            market_id=position.market_id,
            market_slug=market.slug if market else "",
            market_title=market.title if market else "",
            market_status=market.status.value if market else "unknown",
            outcome=position.outcome,
            shares=float(position.shares),
            cost_basis=cost_basis,
            current_value=current_value,
            unrealized_pl=unrealized_pl,
            realized_pl=position_realized_pl,
        )
        if market and market.status.value == "resolved":
            settled_positions.append(payload)
        else:
            open_positions.append(payload)

    thesis_runs = [run for run in all_runs if run.thesis_summary]
    confidences = [float(run.confidence) for run in thesis_runs if run.confidence is not None]
    research_runs = [run for run in thesis_runs if isinstance(run.decision_payload_json, dict) and (run.decision_payload_json.get("thesis_writer", {}).get("search_enabled") or run.decision_payload_json.get("search_enabled"))]
    stored_citations = 0
    external_citations = 0
    for run in thesis_runs:
        for citation in run.citations_json or []:
            citation_type = citation.get("type") if isinstance(citation, dict) else "note"
            if citation_type == "stored_dataset":
                stored_citations += 1
            elif citation_type == "external_web":
                external_citations += 1
    portfolio_value = (float(wallet.balance) if wallet else 0.0) + open_value
    return PublicBotProfileOut(
        id=bot.id,
        display_name=bot.display_name,
        persona=bot.persona,
        strategy_type=bot.strategy_type,
        status=bot.status.value if hasattr(bot.status, "value") else str(bot.status),
        wallet_balance=float(wallet.balance) if wallet else 0.0,
        portfolio_value=portfolio_value,
        total_cost_basis=total_cost_basis,
        total_unrealized_pl=open_value - open_cost_basis,
        realized_pl=realized_pl,
        thesis_count=len(thesis_runs),
        thesis_backed_trade_count=len([run for run in thesis_runs if run.order_id is not None]),
        avg_confidence=(sum(confidences) / len(confidences)) if confidences else None,
        commentary_mode=(bot.tool_config_json or {}).get("commentary_mode"),
        search_enabled=bool((bot.tool_config_json or {}).get("search_enabled")),
        research_runs=len(research_runs),
        stored_citation_count=stored_citations,
        external_citation_count=external_citations,
        last_ran_at=str(bot.last_ran_at) if bot.last_ran_at else None,
        open_positions=open_positions if include_detail else [],
        settled_positions=settled_positions if include_detail else [],
        recent_runs=[_serialize_public_run(run) for run in runs],
    )


@router.get("/public", response_model=list[PublicBotProfileOut])
def list_public_bots(db: Session = Depends(get_db)):
    bots = db.scalars(select(BotProfile).order_by(BotProfile.id.asc())).all()
    return [_serialize_public_bot(db, bot) for bot in bots]


@router.get("/public/leaderboard", response_model=BotLeaderboardOut)
def bot_leaderboard(db: Session = Depends(get_db)):
    bots = db.scalars(select(BotProfile).order_by(BotProfile.id.asc())).all()
    payload = [_serialize_public_bot(db, bot) for bot in bots]
    payload.sort(key=lambda bot: (bot.portfolio_value, bot.realized_pl, bot.thesis_backed_trade_count), reverse=True)
    return BotLeaderboardOut(bots=payload)


@router.get("/public/theses", response_model=BotThesisFeedOut)
def bot_thesis_feed(db: Session = Depends(get_db)):
    runs = db.scalars(
        select(BotRun)
        .where(BotRun.status == "completed", BotRun.thesis_summary.is_not(None))
        .order_by(BotRun.id.desc())
        .limit(50)
    ).all()
    return BotThesisFeedOut(theses=[_serialize_public_run(run) for run in runs])


@router.get("/public/{bot_id}", response_model=PublicBotProfileOut)
def get_public_bot(bot_id: int, db: Session = Depends(get_db)):
    bot = db.scalar(select(BotProfile).where(BotProfile.id == bot_id))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return _serialize_public_bot(db, bot, include_detail=True)


@router.get("", response_model=list[BotProfileOut])
def list_bots(
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    bots = db.scalars(select(BotProfile).order_by(BotProfile.id.asc())).all()
    return [BotProfileOut(**serialize_profile(db, bot)) for bot in bots]


@router.post("", response_model=BotProfileOut)
def create_bot(
    payload: BotProfileCreateIn,
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    try:
        bot = create_bot_profile(db, payload)
        db.commit()
        db.refresh(bot)
        return BotProfileOut(**serialize_profile(db, bot))
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/seed/defaults", response_model=ArenaSeedOut)
def seed_bots(
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    bots = seed_default_bots(db)
    db.commit()
    market_count = len(db.scalars(select(Market)).all())
    return ArenaSeedOut(bot_count=len(bots), market_count=market_count, status="seeded")


@router.post("/arena/reset", response_model=ArenaSeedOut)
def reset_arena(
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    reset_arena_state(db)
    db.commit()
    return ArenaSeedOut(bot_count=0, market_count=0, status="reset")


@router.get("/scheduler/status", response_model=BotSchedulerStatusOut)
def scheduler_status(admin=Depends(require_tier(UserTier.admin))):
    return BotSchedulerStatusOut(**scheduler.status())


@router.post("/scheduler/start", response_model=BotSchedulerStatusOut)
def scheduler_start(admin=Depends(require_tier(UserTier.admin))):
    scheduler.start()
    return BotSchedulerStatusOut(**scheduler.status())


@router.post("/scheduler/stop", response_model=BotSchedulerStatusOut)
def scheduler_stop(admin=Depends(require_tier(UserTier.admin))):
    scheduler.stop()
    return BotSchedulerStatusOut(**scheduler.status())


@router.post("/run-cycle", response_model=list[BotRunOut])
def run_cycle_now(
    payload: BotCycleRunIn,
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    runs = run_cycle(
        db,
        trigger_source=payload.trigger_source,
        market_slug=payload.market_slug,
        bot_profile_id=payload.bot_profile_id,
    )
    db.commit()
    return [BotRunOut(**serialize_run(run)) for run in runs]


@router.get("/{bot_id}", response_model=BotProfileOut)
def get_bot(
    bot_id: int,
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    bot = db.scalar(select(BotProfile).where(BotProfile.id == bot_id))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return BotProfileOut(**serialize_profile(db, bot))


@router.post("/{bot_id}", response_model=BotProfileOut)
def update_bot(
    bot_id: int,
    payload: BotProfileUpdateIn,
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    bot = db.scalar(select(BotProfile).where(BotProfile.id == bot_id))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if key == "status":
            value = BotStatus(value)
        setattr(bot, key, value)
    db.commit()
    db.refresh(bot)
    return BotProfileOut(**serialize_profile(db, bot))


@router.post("/{bot_id}/run", response_model=BotRunOut)
def run_single_bot(
    bot_id: int,
    payload: BotCycleRunIn,
    admin=Depends(require_tier(UserTier.admin)),
    db: Session = Depends(get_db),
):
    bot = db.scalar(select(BotProfile).where(BotProfile.id == bot_id))
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    if not payload.market_slug:
        raise HTTPException(status_code=400, detail="market_slug is required")
    market = get_market_by_slug(db, payload.market_slug)
    run = run_bot_for_market(db, bot=bot, market=market, trigger_source=payload.trigger_source)
    db.commit()
    return BotRunOut(**serialize_run(run))
