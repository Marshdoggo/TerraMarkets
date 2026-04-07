from __future__ import annotations

from pydantic import BaseModel, Field


class BotProfileCreateIn(BaseModel):
    email: str
    password: str = Field(default="botpass123", min_length=8)
    display_name: str
    persona: str
    strategy_type: str
    cadence_minutes: int = Field(default=15, ge=1, le=1440)
    bankroll_target: float = Field(default=1000, gt=0)
    max_trade_amount: float = Field(default=75, gt=0)
    max_market_exposure: float = Field(default=250, gt=0)
    config_json: dict = Field(default_factory=dict)
    tool_config_json: dict | None = None
    wallet_funding: float = Field(default=1000, ge=0)


class BotProfileUpdateIn(BaseModel):
    display_name: str | None = None
    persona: str | None = None
    strategy_type: str | None = None
    status: str | None = None
    cadence_minutes: int | None = Field(default=None, ge=1, le=1440)
    bankroll_target: float | None = Field(default=None, gt=0)
    max_trade_amount: float | None = Field(default=None, gt=0)
    max_market_exposure: float | None = Field(default=None, gt=0)
    config_json: dict | None = None
    tool_config_json: dict | None = None


class BotRunOut(BaseModel):
    id: int
    market_id: int | None = None
    market_slug: str | None = None
    trigger_source: str
    status: str
    action_type: str
    outcome: str | None = None
    shares: float | None = None
    confidence: float | None = None
    thesis_summary: str | None = None
    error_message: str | None = None
    order_id: int | None = None
    started_at: str
    finished_at: str | None = None


class BotProfileOut(BaseModel):
    id: int
    user_id: int
    email: str
    display_name: str
    persona: str
    strategy_type: str
    status: str
    cadence_minutes: int
    bankroll_target: float
    max_trade_amount: float
    max_market_exposure: float
    config_json: dict
    tool_config_json: dict | None = None
    wallet_balance: float
    last_ran_at: str | None = None
    recent_runs: list[BotRunOut] = Field(default_factory=list)


class BotSchedulerStatusOut(BaseModel):
    running: bool
    poll_interval_seconds: int
    last_tick_at: str | None = None


class BotCycleRunIn(BaseModel):
    trigger_source: str = "manual"
    market_slug: str | None = None
    bot_profile_id: int | None = None


class ArenaSeedOut(BaseModel):
    bot_count: int
    market_count: int
    status: str


class PublicBotRunOut(BaseModel):
    id: int
    market_id: int | None = None
    market_slug: str | None = None
    market_title: str | None = None
    trigger_source: str
    action_type: str
    outcome: str | None = None
    shares: float | None = None
    confidence: float | None = None
    thesis_summary: str | None = None
    started_at: str
    finished_at: str | None = None


class PublicBotPositionOut(BaseModel):
    market_id: int
    market_slug: str
    market_title: str
    market_status: str
    outcome: str
    shares: float
    cost_basis: float
    current_value: float | None = None
    unrealized_pl: float | None = None
    realized_pl: float | None = None


class PublicBotProfileOut(BaseModel):
    id: int
    display_name: str
    persona: str
    strategy_type: str
    status: str
    wallet_balance: float
    portfolio_value: float
    total_cost_basis: float
    total_unrealized_pl: float
    realized_pl: float
    thesis_count: int
    thesis_backed_trade_count: int
    avg_confidence: float | None = None
    last_ran_at: str | None = None
    open_positions: list[PublicBotPositionOut] = Field(default_factory=list)
    settled_positions: list[PublicBotPositionOut] = Field(default_factory=list)
    recent_runs: list[PublicBotRunOut] = Field(default_factory=list)


class BotLeaderboardOut(BaseModel):
    bots: list[PublicBotProfileOut]


class BotThesisFeedOut(BaseModel):
    theses: list[PublicBotRunOut]
