from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class MarketCreateIn(BaseModel):
    slug: str = Field(..., min_length=3, max_length=120)
    title: str
    category: str = Field(..., min_length=2, max_length=120)
    description: Optional[str] = None
    resolution_criteria: str = Field(..., min_length=10, max_length=4000)
    close_at: datetime
    outcomes: List[str] = Field(..., min_length=2)
    b: float = Field(50, gt=0)


class MarketOut(BaseModel):
    id: int
    slug: str
    title: str
    category: str
    description: Optional[str]
    resolution_criteria: str
    close_at: str
    status: str
    outcomes: List[str]
    b: float
    q: Dict[str, float]
    prices: Dict[str, float]
    resolved_outcome: Optional[str] = None


class TradeIn(BaseModel):
    outcome: str
    shares: float = Field(..., gt=0)


class TradeOut(BaseModel):
    order_id: int
    cost: float
    avg_price: float
    new_prices: Dict[str, float]


class ResolveIn(BaseModel):
    outcome: str


class SettlementOut(BaseModel):
    market_id: int
    outcome: str
    total_paid: float


class MarketSnapshotOut(BaseModel):
    id: int
    event_type: str
    prices: Dict[str, float]
    q: Dict[str, float]
    total_cost: float
    created_at: str


class MarketDataLinkIn(BaseModel):
    source_key: str
    series_key: str
    label: str
    notes: Optional[str] = None


class LinkedSeriesPointOut(BaseModel):
    observed_at: str
    numeric_value: Optional[float] = None


class MarketDataLinkOut(BaseModel):
    id: int
    source_key: str
    series_key: str
    label: str
    notes: Optional[str] = None
    latest_numeric_value: Optional[float] = None
    latest_unit: Optional[str] = None
    latest_observed_at: Optional[str] = None
    recent_points: List[LinkedSeriesPointOut] = []


class MarketDetailOut(MarketOut):
    snapshots: List[MarketSnapshotOut] = []
    data_links: List[MarketDataLinkOut] = []


class BotCommentaryOut(BaseModel):
    id: int
    market_slug: Optional[str] = None
    bot_display_name: str
    bot_persona: str
    strategy_type: str
    action_type: str
    outcome: Optional[str] = None
    shares: Optional[float] = None
    confidence: Optional[float] = None
    thesis_summary: Optional[str] = None
    created_at: str


class DemoSeedPipelineOut(BaseModel):
    source_key: str
    pipeline_label: str
    created_markets: int
    existing_markets: int
    created_links: int
    existing_links: int


class DemoSeedSummaryOut(BaseModel):
    created_markets: int
    existing_markets: int
    created_links: int
    existing_links: int
    pipelines: List[DemoSeedPipelineOut] = []
