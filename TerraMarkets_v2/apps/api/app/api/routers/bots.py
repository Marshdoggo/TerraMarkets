from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_tier
from app.core.db import get_db
from app.models.bot import BotProfile
from app.models.market import Market
from app.models.enums import BotStatus, UserTier
from app.schemas.bot import ArenaSeedOut, BotCycleRunIn, BotProfileCreateIn, BotProfileOut, BotProfileUpdateIn, BotRunOut, BotSchedulerStatusOut
from app.services.bot_service import create_bot_profile, reset_arena_state, run_bot_for_market, run_cycle, scheduler, seed_default_bots, serialize_profile, serialize_run
from app.services.trading_service import get_market_by_slug

router = APIRouter(prefix="/bots", tags=["bots"])


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
