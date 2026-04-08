from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Lock, Thread
from time import sleep

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import db as core_db
from app.core.config import settings
from app.models.bot import BotProfile, BotRun
from app.models.enums import BotStatus, MarketStatus
from app.models.market import Market
from app.models.market_data_link import MarketDataLink
from app.models.market_snapshot import MarketSnapshot
from app.models.order import Order
from app.models.position import Position
from app.models.user import User
from app.models.wallet import LedgerEntry, Wallet
from app.services.auth_service import register_user
from app.services.data_service import list_recent_points_for_series
from app.services.trading_service import execute_buy, market_prices

DEFAULT_BOT_PASSWORD = "botpass123"
SCHEDULER_POLL_INTERVAL_SECONDS = 15

DEFAULT_BOT_SPECS = [
    {
        "email": "trend.talia@bots.terramarkets.dev",
        "display_name": "Trend Talia",
        "persona": "Momentum trader who leans into strengthening market leaders and avoids overpaying.",
        "strategy_type": "trend_follower",
        "cadence_minutes": 15,
        "bankroll_target": 1400,
        "max_trade_amount": 90,
        "max_market_exposure": 275,
        "config_json": {"momentum_threshold": 0.02, "event_driven_on_data": True},
        "tool_config_json": {
            "thesis_writer_enabled": True,
            "voice_style": "Momentum-first, price-action focused, and crisp. Talk about strengthening trends, confirmation, and follow-through without sounding reckless.",
            "citation_mode": "stored_datasets_only",
            "tone_hints": "Confident, concise, tape-reader energy.",
            "max_thesis_chars": 420,
        },
        "wallet_funding": 1400,
    },
    {
        "email": "spec.sam@bots.terramarkets.dev",
        "display_name": "Spec Sam",
        "persona": "Contrarian speculator who buys underpriced outcomes when market odds look stretched.",
        "strategy_type": "speculator",
        "cadence_minutes": 20,
        "bankroll_target": 1300,
        "max_trade_amount": 70,
        "max_market_exposure": 220,
        "config_json": {"value_threshold": 0.42, "min_spread": 0.08, "event_driven_on_data": True},
        "tool_config_json": {
            "thesis_writer_enabled": True,
            "voice_style": "Contrarian, skeptical, and edge-seeking. Emphasize crowd overreaction, stretched pricing, and asymmetric entry points.",
            "citation_mode": "stored_datasets_only",
            "tone_hints": "Wry, sharp, and opportunistic without being flippant.",
            "max_thesis_chars": 420,
        },
        "wallet_funding": 1300,
    },
    {
        "email": "hedge.hana@bots.terramarkets.dev",
        "display_name": "Hedge Hana",
        "persona": "Risk balancer who limits concentration and adds exposure to the cheapest complementary side.",
        "strategy_type": "hedger",
        "cadence_minutes": 25,
        "bankroll_target": 1250,
        "max_trade_amount": 55,
        "max_market_exposure": 200,
        "config_json": {"rebalance_threshold": 0.65, "event_driven_on_data": True},
        "tool_config_json": {
            "thesis_writer_enabled": True,
            "voice_style": "Calm, portfolio-aware, and risk-centered. Explain concentration, diversification, and downside control in steady language.",
            "citation_mode": "stored_datasets_only",
            "tone_hints": "Measured, composed, and quietly analytical.",
            "max_thesis_chars": 420,
        },
        "wallet_funding": 1250,
    },
    {
        "email": "claw.cora@bots.terramarkets.dev",
        "display_name": "Claw Cora",
        "persona": "Research-oriented OpenClaw prototype that records a thesis format compatible with future web-search tooling.",
        "strategy_type": "openclaw_agent",
        "cadence_minutes": 30,
        "bankroll_target": 1500,
        "max_trade_amount": 80,
        "max_market_exposure": 240,
        "config_json": {"event_driven_on_data": True, "mode": "research_adapter"},
        "tool_config_json": {
            "adapter": "openai",
            "thesis_writer_enabled": False,
            "voice_style": "Research-heavy, synthesis-oriented, and exploratory. Weigh multiple signals and explain uncertainty directly.",
            "citation_mode": "stored_datasets_only",
            "tone_hints": "Curious, incisive, and evidence-driven.",
            "max_thesis_chars": 520,
        },
        "wallet_funding": 1500,
    },
]


@dataclass
class BotDecision:
    action_type: str
    outcome: str | None = None
    shares: float | None = None
    confidence: float | None = None
    thesis_summary: str | None = None
    citations: list[str] | None = None
    payload: dict | None = None


class StrategyAdapter:
    def decide(self, context: dict) -> BotDecision:
        raise NotImplementedError


class TrendFollowerStrategy(StrategyAdapter):
    def decide(self, context: dict) -> BotDecision:
        prices = context["prices"]
        snapshots = context["snapshots"]
        ranked = sorted(prices.items(), key=lambda item: item[1], reverse=True)
        if not ranked:
            return BotDecision(action_type="hold", thesis_summary="No priced outcomes available.")
        leader, leader_price = ranked[0]
        previous_prices = snapshots[1].prices if len(snapshots) > 1 else {}
        prior_leader_price = float(previous_prices.get(leader, leader_price))
        momentum = float(leader_price) - prior_leader_price
        threshold = float(context["bot"].config_json.get("momentum_threshold", 0.02))
        if momentum < threshold:
            return BotDecision(
                action_type="hold",
                confidence=max(0.15, min(0.55, leader_price)),
                thesis_summary=f"Leader {leader} is ahead, but momentum ({momentum:.3f}) is below threshold.",
                payload={"leader": leader, "momentum": momentum},
            )
        shares = context["share_budget"] / max(leader_price, 0.15)
        return BotDecision(
            action_type="buy",
            outcome=leader,
            shares=max(1.0, round(shares, 2)),
            confidence=min(0.95, max(0.55, leader_price + momentum)),
            thesis_summary=f"Momentum favors {leader}; price rose from {prior_leader_price:.2f} to {leader_price:.2f}.",
            payload={"leader": leader, "momentum": momentum},
        )


class SpeculatorStrategy(StrategyAdapter):
    def decide(self, context: dict) -> BotDecision:
        prices = context["prices"]
        ranked = sorted(prices.items(), key=lambda item: item[1])
        if len(ranked) < 2:
            return BotDecision(action_type="hold", thesis_summary="Not enough outcomes for contrarian pricing.")
        target, target_price = ranked[0]
        next_price = ranked[1][1]
        min_spread = float(context["bot"].config_json.get("min_spread", 0.08))
        value_threshold = float(context["bot"].config_json.get("value_threshold", 0.42))
        spread = float(next_price) - float(target_price)
        if target_price > value_threshold or spread < min_spread:
            return BotDecision(
                action_type="hold",
                confidence=0.4,
                thesis_summary=f"No obvious discount: cheapest outcome {target} is priced at {target_price:.2f}.",
                payload={"target": target, "spread": spread},
            )
        shares = context["share_budget"] / max(target_price, 0.12)
        return BotDecision(
            action_type="buy",
            outcome=target,
            shares=max(1.0, round(shares, 2)),
            confidence=min(0.9, max(0.52, 1 - target_price)),
            thesis_summary=f"Contrarian entry on {target}; market spread of {spread:.2f} suggests mispricing.",
            payload={"target": target, "spread": spread},
        )


class HedgerStrategy(StrategyAdapter):
    def decide(self, context: dict) -> BotDecision:
        prices = context["prices"]
        exposure_by_outcome = context["exposure_by_outcome"]
        total_exposure = sum(exposure_by_outcome.values())
        ranked = sorted(prices.items(), key=lambda item: item[1])
        if not ranked:
            return BotDecision(action_type="hold", thesis_summary="No outcomes available for hedging.")
        cheapest_outcome, cheapest_price = ranked[0]
        dominant_outcome = None
        dominant_ratio = 0.0
        if total_exposure > 0:
            dominant_outcome, dominant_value = max(exposure_by_outcome.items(), key=lambda item: item[1])
            dominant_ratio = dominant_value / total_exposure if total_exposure else 0.0
        threshold = float(context["bot"].config_json.get("rebalance_threshold", 0.65))
        alternative_outcomes = [(outcome, price) for outcome, price in ranked if outcome != dominant_outcome]
        target_outcome = None
        if dominant_ratio >= threshold and alternative_outcomes:
            target_outcome = alternative_outcomes[0][0]
        elif cheapest_outcome != dominant_outcome:
            target_outcome = cheapest_outcome
        if target_outcome is None and total_exposure > 0:
            return BotDecision(
                action_type="hold",
                confidence=0.35,
                thesis_summary="Exposure is already balanced across outcomes.",
                payload={"dominant_ratio": dominant_ratio},
            )
        if target_outcome is None:
            target_outcome = cheapest_outcome
        shares = context["share_budget"] / max(prices[target_outcome], 0.15)
        return BotDecision(
            action_type="buy",
            outcome=target_outcome,
            shares=max(1.0, round(shares, 2)),
            confidence=min(0.8, max(0.45, 1 - cheapest_price)),
            thesis_summary=f"Rebalancing toward {target_outcome} to reduce concentration risk.",
            payload={"dominant_ratio": dominant_ratio, "target_outcome": target_outcome},
        )


class AgentPolicyAdapter(StrategyAdapter):
    def decide(self, context: dict) -> BotDecision:
        strategy_type = context["bot"].strategy_type
        return BotDecision(
            action_type="hold",
            confidence=0.25,
            thesis_summary=f"Agent policy adapter for {strategy_type} is configured but not yet connected to a tool runtime.",
            payload={"mode": "deferred_agent_adapter"},
        )


def _extract_response_text(payload: dict) -> str:
    if payload.get("output_text"):
        return str(payload["output_text"])
    fragments: list[str] = []
    for output in payload.get("output", []) or []:
        for content in output.get("content", []) or []:
            text = content.get("text")
            if text:
                fragments.append(str(text))
    return "\n".join(fragments).strip()


def _bounded_float(value, *, default: float, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))


def _bot_tool_config(bot: BotProfile | object) -> dict:
    config = getattr(bot, "tool_config_json", None)
    return config if isinstance(config, dict) else {}


def _recent_snapshot_payload(context: dict, limit: int = 5) -> list[dict]:
    return [
        {"event_type": snapshot.event_type, "prices": snapshot.prices, "created_at": str(snapshot.created_at)}
        for snapshot in context["snapshots"][:limit]
    ]


def _linked_dataset_citations(context: dict) -> list[str]:
    citations: list[str] = []
    for dataset in context.get("linked_data_points", []):
        label = dataset.get("label") or dataset.get("series_key") or dataset.get("source_key") or "dataset"
        source_key = dataset.get("source_key") or "unknown-source"
        series_key = dataset.get("series_key") or "unknown-series"
        citations.append(f"{label} ({source_key}/{series_key})")
    return citations


def should_generate_thesis_for_decision(decision: BotDecision) -> bool:
    if decision.action_type == "buy":
        return True
    if decision.action_type != "hold":
        return False
    thesis = (decision.thesis_summary or "").strip()
    if len(thesis) < 50:
        return False
    return len(thesis.split()) >= 8


def _sanitize_dataset_citations(citations: list[str] | None, *, allowed: list[str]) -> list[str]:
    if not citations:
        return []
    allowed_map = {entry.lower(): entry for entry in allowed}
    cleaned: list[str] = []
    for citation in citations:
        text = str(citation).strip()
        if not text:
            continue
        if text.lower().startswith("http://") or text.lower().startswith("https://"):
            continue
        matched = None
        lowered = text.lower()
        for allowed_key, allowed_value in allowed_map.items():
            if lowered == allowed_key or lowered in allowed_key or allowed_key in lowered:
                matched = allowed_value
                break
        if matched and matched not in cleaned:
            cleaned.append(matched)
    return cleaned[:5]


def _call_openai_responses(*, model: str, instructions: str, prompt_payload: dict) -> dict:
    response = httpx.post(
        "https://api.openai.com/v1/responses",
        headers={
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(prompt_payload, default=str)},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    raw_text = _extract_response_text(response.json())
    return json.loads(raw_text)


class OpenAIBotStrategy(StrategyAdapter):
    def decide(self, context: dict) -> BotDecision:
        bot = context["bot"]
        if not settings.OPENAI_BOT_ENABLED:
            return BotDecision(
                action_type="hold",
                confidence=0.25,
                thesis_summary="OpenAI bot reasoning is disabled. Set OPENAI_BOT_ENABLED=true to enable live thesis generation.",
                payload={"mode": "openai_disabled"},
            )
        if not settings.OPENAI_API_KEY:
            return BotDecision(
                action_type="hold",
                confidence=0.25,
                thesis_summary="OpenAI bot reasoning is configured but OPENAI_API_KEY is missing.",
                payload={"mode": "openai_missing_key"},
            )

        market = context["market"]
        allowed_outcomes = list(market.outcomes or [])
        prompt_payload = {
            "bot": {
                "display_name": bot.display_name,
                "persona": bot.persona,
                "strategy_type": bot.strategy_type,
                "max_trade_amount": float(bot.max_trade_amount),
                "max_market_exposure": float(bot.max_market_exposure),
            },
            "market": {
                "slug": market.slug,
                "title": market.title,
                "category": market.category,
                "description": market.description,
                "resolution_criteria": market.resolution_criteria,
                "outcomes": allowed_outcomes,
                "prices": context["prices"],
                "recent_snapshots": _recent_snapshot_payload(context),
            },
            "risk": {
                "share_budget": context["share_budget"],
                "exposure_total": context["exposure_total"],
                "exposure_by_outcome": context["exposure_by_outcome"],
            },
            "linked_datasets": context.get("linked_data_points", []),
        }
        instructions = (
            "You are a TerraMarkets forecasting bot. Use only the provided market and stored dataset context. "
            "Return strict JSON with keys: action_type, outcome, shares, confidence, thesis_summary, citations, rationale. "
            "action_type must be buy or hold. If buying, outcome must be one of the allowed market outcomes. "
            "Keep thesis_summary to 1-3 concise sentences and do not claim external web research."
        )
        try:
            parsed = _call_openai_responses(
                model=settings.OPENAI_BOT_MODEL,
                instructions=instructions,
                prompt_payload=prompt_payload,
            )
        except Exception as exc:
            return BotDecision(
                action_type="hold",
                confidence=0.2,
                thesis_summary="OpenAI thesis generation failed; holding until the next bot cycle.",
                payload={"mode": "openai_error", "error": str(exc)},
            )

        action_type = "buy" if str(parsed.get("action_type", "hold")).lower() == "buy" else "hold"
        outcome = parsed.get("outcome") if parsed.get("outcome") in allowed_outcomes else None
        confidence = _bounded_float(parsed.get("confidence"), default=0.4, minimum=0.0, maximum=1.0)
        share_budget = float(context.get("share_budget") or 0)
        requested_shares = _bounded_float(parsed.get("shares"), default=0.0, minimum=0.0, maximum=10_000.0)
        if action_type == "buy":
            if not outcome or share_budget <= 0:
                action_type = "hold"
                outcome = None
                requested_shares = None
            else:
                implied_price = max(float(context["prices"].get(outcome, 0.2)), 0.1)
                budget_limited_shares = share_budget / implied_price
                requested_shares = max(1.0, min(requested_shares or budget_limited_shares, budget_limited_shares))
        else:
            outcome = None
            requested_shares = None

        thesis_summary = str(parsed.get("thesis_summary") or "No thesis supplied.").strip()[:1200]
        citations = parsed.get("citations") if isinstance(parsed.get("citations"), list) else []
        return BotDecision(
            action_type=action_type,
            outcome=outcome,
            shares=round(float(requested_shares), 6) if requested_shares else None,
            confidence=confidence,
            thesis_summary=thesis_summary,
            citations=[str(citation)[:500] for citation in citations[:5]],
            payload={"mode": "openai_responses", "model": settings.OPENAI_BOT_MODEL, "rationale": parsed.get("rationale")},
        )


class OpenAIThesisWriter:
    def rewrite(self, *, context: dict, decision: BotDecision) -> BotDecision:
        if not settings.OPENAI_BOT_THESIS_ENABLED:
            return decision
        if not settings.OPENAI_API_KEY:
            return decision

        bot = context["bot"]
        tool_config = _bot_tool_config(bot)
        if tool_config.get("thesis_writer_enabled") is False:
            return decision
        if not should_generate_thesis_for_decision(decision):
            return decision

        market = context["market"]
        allowed_citations = _linked_dataset_citations(context)
        max_thesis_chars = int(tool_config.get("max_thesis_chars", 420))
        prompt_payload = {
            "bot": {
                "display_name": bot.display_name,
                "persona": bot.persona,
                "strategy_type": bot.strategy_type,
                "voice_style": tool_config.get("voice_style"),
                "tone_hints": tool_config.get("tone_hints"),
            },
            "market": {
                "slug": market.slug,
                "title": market.title,
                "category": market.category,
                "description": market.description,
                "resolution_criteria": market.resolution_criteria,
                "outcomes": list(market.outcomes or []),
                "prices": context["prices"],
                "recent_snapshots": _recent_snapshot_payload(context),
            },
            "decision": {
                "action_type": decision.action_type,
                "outcome": decision.outcome,
                "shares": decision.shares,
                "confidence": decision.confidence,
                "thesis_summary": decision.thesis_summary,
                "payload": decision.payload or {},
            },
            "linked_datasets": context.get("linked_data_points", []),
            "allowed_citations": allowed_citations,
        }
        instructions = (
            "You are polishing a TerraMarkets bot thesis. Preserve the bot's existing action_type, outcome, and overall bias. "
            "Do not introduce web claims, URLs, or outside research. Use only the provided stored datasets and market context. "
            "Return strict JSON with keys: thesis_summary, confidence, citations, voice_tags, rationale. "
            f"Keep thesis_summary in character, 1-3 sentences, and under {max_thesis_chars} characters."
        )
        try:
            parsed = _call_openai_responses(
                model=settings.OPENAI_BOT_THESIS_MODEL or settings.OPENAI_BOT_MODEL,
                instructions=instructions,
                prompt_payload=prompt_payload,
            )
        except Exception as exc:
            payload = dict(decision.payload or {})
            payload["thesis_writer"] = {"status": "error", "error": str(exc)}
            decision.payload = payload
            return decision

        thesis_summary = str(parsed.get("thesis_summary") or decision.thesis_summary or "").strip()
        if not thesis_summary:
            return decision
        citations = _sanitize_dataset_citations(parsed.get("citations"), allowed=allowed_citations)
        confidence = decision.confidence
        if parsed.get("confidence") is not None:
            confidence = _bounded_float(parsed.get("confidence"), default=decision.confidence or 0.4, minimum=0.0, maximum=1.0)

        payload = dict(decision.payload or {})
        payload["thesis_writer"] = {
            "status": "rewritten",
            "model": settings.OPENAI_BOT_THESIS_MODEL or settings.OPENAI_BOT_MODEL,
            "voice_tags": parsed.get("voice_tags"),
            "rationale": parsed.get("rationale"),
            "citation_mode": tool_config.get("citation_mode", "stored_datasets_only"),
        }
        return BotDecision(
            action_type=decision.action_type,
            outcome=decision.outcome,
            shares=decision.shares,
            confidence=confidence,
            thesis_summary=thesis_summary[:max_thesis_chars],
            citations=citations or decision.citations,
            payload=payload,
        )


STRATEGIES: dict[str, StrategyAdapter] = {
    "trend_follower": TrendFollowerStrategy(),
    "speculator": SpeculatorStrategy(),
    "hedger": HedgerStrategy(),
    "openclaw_agent": OpenAIBotStrategy(),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def serialize_run(run: BotRun) -> dict:
    return {
        "id": run.id,
        "market_id": run.market_id,
        "market_slug": run.market.slug if run.market else None,
        "trigger_source": run.trigger_source,
        "status": run.status,
        "action_type": run.action_type,
        "outcome": run.outcome,
        "shares": float(run.shares) if run.shares is not None else None,
        "confidence": float(run.confidence) if run.confidence is not None else None,
        "thesis_summary": run.thesis_summary,
        "error_message": run.error_message,
        "order_id": run.order_id,
        "started_at": str(run.started_at),
        "finished_at": str(run.finished_at) if run.finished_at else None,
    }


def serialize_profile(db: Session, bot: BotProfile, include_runs: bool = True) -> dict:
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == bot.user_id))
    payload = {
        "id": bot.id,
        "user_id": bot.user_id,
        "email": bot.user.email,
        "display_name": bot.display_name,
        "persona": bot.persona,
        "strategy_type": bot.strategy_type,
        "status": bot.status.value if hasattr(bot.status, "value") else str(bot.status),
        "cadence_minutes": bot.cadence_minutes,
        "bankroll_target": float(bot.bankroll_target),
        "max_trade_amount": float(bot.max_trade_amount),
        "max_market_exposure": float(bot.max_market_exposure),
        "config_json": bot.config_json or {},
        "tool_config_json": bot.tool_config_json,
        "wallet_balance": float(wallet.balance) if wallet else 0.0,
        "last_ran_at": str(bot.last_ran_at) if bot.last_ran_at else None,
        "recent_runs": [],
    }
    if include_runs:
        runs = db.scalars(
            select(BotRun).where(BotRun.bot_profile_id == bot.id).order_by(BotRun.id.desc()).limit(10)
        ).all()
        payload["recent_runs"] = [serialize_run(run) for run in runs]
    return payload


def get_open_markets(db: Session, market_slug: str | None = None) -> list[Market]:
    query = select(Market).where(Market.status == MarketStatus.open)
    if market_slug:
        query = query.where(Market.slug == market_slug)
    return db.scalars(query.order_by(Market.id.asc())).all()


def get_bot_profiles(db: Session, *, active_only: bool = False, bot_profile_id: int | None = None) -> list[BotProfile]:
    query = select(BotProfile)
    if active_only:
        query = query.where(BotProfile.status == BotStatus.active)
    if bot_profile_id is not None:
        query = query.where(BotProfile.id == bot_profile_id)
    return db.scalars(query.order_by(BotProfile.id.asc())).all()


def bot_market_cost_basis(db: Session, *, bot: BotProfile, market: Market) -> tuple[float, dict[str, float]]:
    orders = db.scalars(select(Order).where(Order.user_id == bot.user_id, Order.market_id == market.id)).all()
    exposure_by_outcome: dict[str, float] = {}
    total = 0.0
    for order in orders:
        exposure_by_outcome.setdefault(order.outcome, 0.0)
        exposure_by_outcome[order.outcome] += float(order.cost)
        total += float(order.cost)
    return total, exposure_by_outcome


def compute_share_budget(bot: BotProfile, wallet: Wallet, current_exposure: float) -> float:
    balance_cap = min(float(wallet.balance), float(bot.max_trade_amount))
    exposure_room = max(0.0, float(bot.max_market_exposure) - current_exposure)
    return round(max(0.0, min(balance_cap, exposure_room)), 6)


def strategy_for_bot(bot: BotProfile) -> StrategyAdapter:
    if (bot.tool_config_json or {}).get("adapter") == "openai":
        return OpenAIBotStrategy()
    return STRATEGIES.get(bot.strategy_type, AgentPolicyAdapter())


def build_context(db: Session, *, bot: BotProfile, market: Market) -> dict:
    wallet = db.scalar(select(Wallet).where(Wallet.user_id == bot.user_id))
    snapshots = db.scalars(
        select(MarketSnapshot).where(MarketSnapshot.market_id == market.id).order_by(MarketSnapshot.id.desc()).limit(5)
    ).all()
    total_exposure, exposure_by_outcome = bot_market_cost_basis(db, bot=bot, market=market)
    linked_series = db.scalars(
        select(MarketDataLink).where(MarketDataLink.market_id == market.id).order_by(MarketDataLink.id.asc())
    ).all()
    linked_data_points = []
    for link in linked_series:
        linked_data_points.append(
            {
                "source_key": link.source_key,
                "series_key": link.series_key,
                "label": link.label,
                "notes": link.notes,
                "recent_points": [
                    {
                        "observed_at": str(point.observed_at),
                        "numeric_value": float(point.numeric_value) if point.numeric_value is not None else None,
                        "unit": point.unit,
                        "metadata_json": point.metadata_json,
                    }
                    for point in list_recent_points_for_series(
                        db,
                        source_key=link.source_key,
                        series_key=link.series_key,
                        limit=8,
                    )
                ],
            }
        )
    share_budget = compute_share_budget(bot, wallet, total_exposure) if wallet else 0.0
    return {
        "bot": bot,
        "market": market,
        "wallet": wallet,
        "prices": market_prices(market),
        "snapshots": snapshots,
        "exposure_total": total_exposure,
        "exposure_by_outcome": exposure_by_outcome,
        "linked_series": linked_series,
        "linked_data_points": linked_data_points,
        "share_budget": share_budget,
    }


def _finalize_run(run: BotRun, *, status: str, action_type: str, finished_at: datetime, decision: BotDecision | None = None, order_id: int | None = None, error_message: str | None = None) -> None:
    run.status = status
    run.action_type = action_type
    run.finished_at = finished_at
    run.order_id = order_id
    run.error_message = error_message
    if decision:
        run.outcome = decision.outcome
        run.shares = Decimal(str(decision.shares)) if decision.shares is not None else None
        run.confidence = Decimal(str(decision.confidence)) if decision.confidence is not None else None
        run.thesis_summary = decision.thesis_summary
        run.citations_json = decision.citations
        run.decision_payload_json = decision.payload


_ACTIVE_MARKET_RUNS: set[tuple[int, int]] = set()
_ACTIVE_MARKET_RUNS_LOCK = Lock()


def run_bot_for_market(db: Session, *, bot: BotProfile, market: Market, trigger_source: str = "scheduled") -> BotRun:
    key = (bot.id, market.id)
    with _ACTIVE_MARKET_RUNS_LOCK:
        if key in _ACTIVE_MARKET_RUNS:
            raise ValueError("Bot is already evaluating this market.")
        _ACTIVE_MARKET_RUNS.add(key)

    run = BotRun(bot_profile_id=bot.id, market_id=market.id, trigger_source=trigger_source, status="running", action_type="hold")
    db.add(run)
    db.flush()

    try:
        context = build_context(db, bot=bot, market=market)
        wallet = context["wallet"]
        if wallet is None:
            decision = BotDecision(action_type="hold", confidence=0.0, thesis_summary="Bot wallet is missing.")
            _finalize_run(run, status="failed", action_type="hold", finished_at=utcnow(), decision=decision, error_message="Wallet not found.")
            return run
        if context["share_budget"] <= 0:
            decision = BotDecision(action_type="hold", confidence=0.2, thesis_summary="No available budget under balance/exposure limits.")
            _finalize_run(run, status="completed", action_type="hold", finished_at=utcnow(), decision=decision)
            bot.last_ran_at = utcnow()
            return run

        strategy = strategy_for_bot(bot)
        decision = strategy.decide(context)
        if not isinstance(strategy, OpenAIBotStrategy):
            decision = OpenAIThesisWriter().rewrite(context=context, decision=decision)
        action_type = decision.action_type or "hold"
        if action_type != "buy" or not decision.outcome or not decision.shares:
            _finalize_run(run, status="completed", action_type="hold", finished_at=utcnow(), decision=decision)
            bot.last_ran_at = utcnow()
            return run

        shares = min(float(decision.shares), max(1.0, context["share_budget"] / max(context["prices"].get(decision.outcome, 0.2), 0.1)))
        decision.shares = round(shares, 6)
        order = execute_buy(db, market=market, user_id=bot.user_id, outcome=decision.outcome, shares=decision.shares)
        db.flush()
        _finalize_run(run, status="completed", action_type="buy", finished_at=utcnow(), decision=decision, order_id=order.id)
        bot.last_ran_at = utcnow()
        return run
    except Exception as exc:
        decision = locals().get("decision")
        _finalize_run(
            run,
            status="failed",
            action_type="hold",
            finished_at=utcnow(),
            decision=decision if isinstance(decision, BotDecision) else None,
            error_message=str(exc),
        )
        bot.last_ran_at = utcnow()
        return run
    finally:
        with _ACTIVE_MARKET_RUNS_LOCK:
            _ACTIVE_MARKET_RUNS.discard(key)


def run_cycle(db: Session, *, trigger_source: str = "scheduled", market_slug: str | None = None, bot_profile_id: int | None = None) -> list[BotRun]:
    bots = get_bot_profiles(db, active_only=True, bot_profile_id=bot_profile_id)
    markets = get_open_markets(db, market_slug=market_slug)
    runs: list[BotRun] = []
    now = utcnow()
    for bot in bots:
        if trigger_source == "scheduled" and bot.last_ran_at:
            due_at = bot.last_ran_at + timedelta(minutes=bot.cadence_minutes)
            if due_at > now:
                continue
        for market in markets:
            try:
                run = run_bot_for_market(db, bot=bot, market=market, trigger_source=trigger_source)
                runs.append(run)
            except ValueError:
                continue
    return runs


def run_event_driven_for_source(source_key: str) -> list[int]:
    db = core_db.SessionLocal()
    try:
        market_ids = db.scalars(select(MarketDataLink.market_id).where(MarketDataLink.source_key == source_key)).all()
        market_slugs = db.scalars(select(Market.slug).where(Market.id.in_(market_ids))).all() if market_ids else []
        triggered: list[int] = []
        for bot in get_bot_profiles(db, active_only=True):
            if not (bot.config_json or {}).get("event_driven_on_data", False):
                continue
            for market_slug in market_slugs:
                for run in run_cycle(db, trigger_source="data_refresh", market_slug=market_slug, bot_profile_id=bot.id):
                    triggered.append(run.id)
        db.commit()
        return triggered
    finally:
        db.close()


def create_bot_profile(db: Session, payload) -> BotProfile:
    existing = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if existing and existing.bot_profile:
        raise ValueError("Bot user already exists.")
    user = existing or register_user(db, payload.email, payload.password)
    wallet = user.wallet
    target_balance = Decimal(str(payload.wallet_funding))
    delta = target_balance - Decimal(wallet.balance)
    if delta > 0:
        wallet.balance = Decimal(wallet.balance) + delta
        db.add(LedgerEntry(wallet_id=wallet.id, amount=delta, memo="Bot arena funding"))
    bot = BotProfile(
        user_id=user.id,
        display_name=payload.display_name,
        persona=payload.persona,
        strategy_type=payload.strategy_type,
        cadence_minutes=payload.cadence_minutes,
        bankroll_target=payload.bankroll_target,
        max_trade_amount=payload.max_trade_amount,
        max_market_exposure=payload.max_market_exposure,
        config_json=payload.config_json or {},
        tool_config_json=payload.tool_config_json,
        status=BotStatus.active,
    )
    db.add(bot)
    db.flush()
    return bot


def seed_default_bots(db: Session) -> list[BotProfile]:
    from types import SimpleNamespace

    bots: list[BotProfile] = []
    for spec in DEFAULT_BOT_SPECS:
        existing = db.scalar(select(User).where(User.email == spec["email"]))
        if existing and existing.bot_profile:
            bots.append(existing.bot_profile)
            continue
        payload = SimpleNamespace(
            email=spec["email"],
            password=DEFAULT_BOT_PASSWORD,
            display_name=spec["display_name"],
            persona=spec["persona"],
            strategy_type=spec["strategy_type"],
            cadence_minutes=spec["cadence_minutes"],
            bankroll_target=spec["bankroll_target"],
            max_trade_amount=spec["max_trade_amount"],
            max_market_exposure=spec["max_market_exposure"],
            config_json=spec["config_json"],
            tool_config_json=spec.get("tool_config_json"),
            wallet_funding=spec["wallet_funding"],
        )
        bots.append(create_bot_profile(db, payload))
    return bots


def reset_arena_state(db: Session) -> None:
    bot_user_ids = db.scalars(select(BotProfile.user_id)).all()
    db.execute(delete(BotRun))
    db.execute(delete(BotProfile))
    db.execute(delete(Position))
    db.execute(delete(Order))
    db.execute(delete(MarketSnapshot))
    db.execute(delete(MarketDataLink))
    db.execute(delete(Market))
    if bot_user_ids:
        db.execute(delete(LedgerEntry).where(LedgerEntry.wallet_id.in_(select(Wallet.id).where(Wallet.user_id.in_(bot_user_ids)))))
        db.execute(delete(Wallet).where(Wallet.user_id.in_(bot_user_ids)))
        db.execute(delete(User).where(User.id.in_(bot_user_ids)))


class BotArenaScheduler:
    def __init__(self):
        self._lock = Lock()
        self._thread: Thread | None = None
        self._running = False
        self.last_tick_at: datetime | None = None

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = Thread(target=self._loop, name="bot-arena-scheduler", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def status(self) -> dict:
        return {
            "running": self._running,
            "poll_interval_seconds": SCHEDULER_POLL_INTERVAL_SECONDS,
            "last_tick_at": str(self.last_tick_at) if self.last_tick_at else None,
        }

    def _loop(self) -> None:
        while True:
            with self._lock:
                if not self._running:
                    break
            db = core_db.SessionLocal()
            try:
                run_cycle(db, trigger_source="scheduled")
                db.commit()
                self.last_tick_at = utcnow()
            except Exception:
                db.rollback()
                self.last_tick_at = utcnow()
            finally:
                db.close()
            sleep(SCHEDULER_POLL_INTERVAL_SECONDS)


scheduler = BotArenaScheduler()
