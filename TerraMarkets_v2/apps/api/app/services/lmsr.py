from __future__ import annotations

import math
from typing import Dict, List


def cost(q: Dict[str, float], b: float, outcomes: List[str]) -> float:
    total = 0.0
    for outcome in outcomes:
        total += math.exp(float(q.get(outcome, 0.0)) / float(b))
    return float(b) * math.log(total)


def prices(q: Dict[str, float], b: float, outcomes: List[str]) -> Dict[str, float]:
    exps = {outcome: math.exp(float(q.get(outcome, 0.0)) / float(b)) for outcome in outcomes}
    denom = sum(exps.values()) or 1.0
    return {outcome: exps[outcome] / denom for outcome in outcomes}


def trade_cost_delta(q: Dict[str, float], b: float, outcomes: List[str], outcome: str, shares: float) -> float:
    q2 = dict(q)
    q2[outcome] = float(q2.get(outcome, 0.0)) + float(shares)
    return cost(q2, b, outcomes) - cost(q, b, outcomes)


def implied_avg_price(q: Dict[str, float], b: float, outcomes: List[str], outcome: str, shares: float) -> float:
    delta = trade_cost_delta(q, b, outcomes, outcome, shares)
    return float(delta) / float(shares)

