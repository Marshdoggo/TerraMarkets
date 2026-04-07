from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class NormalizedObservation(BaseModel):
    source: str
    metric: str
    timestamp: str
    value: Any
    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineFetchResult(BaseModel):
    source: str
    summary: str
    records: list[NormalizedObservation]
    payload: dict[str, Any] = Field(default_factory=dict)
