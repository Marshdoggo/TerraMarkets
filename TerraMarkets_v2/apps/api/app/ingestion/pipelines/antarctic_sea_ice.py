from __future__ import annotations

from app.ingestion.pipelines.base import BaseIngestionPipeline
from app.ingestion.types import NormalizedObservation, PipelineFetchResult
from app.oracles.nsidc_charctic import NSIDC_ANTARCTIC_DAILY_URL, fetch_nsidc_antarctic_daily


class AntarcticSeaIcePipeline(BaseIngestionPipeline):
    source_key = "nsidc_antarctic_daily"
    label = "NSIDC Antarctic Sea Ice"

    def fetch(self, *, days: int = 365, **kwargs) -> PipelineFetchResult:
        fetched = fetch_nsidc_antarctic_daily(days=days, source_key=self.source_key)
        records = [
            NormalizedObservation(
                source=self.source_key,
                metric=point["series_key"],
                timestamp=point["observed_at"],
                value=point["numeric_value"],
                metadata={
                    **(point.get("metadata_json") or {}),
                    "label": point.get("label"),
                    "unit": point.get("unit"),
                    "source_url": NSIDC_ANTARCTIC_DAILY_URL,
                },
            )
            for point in fetched["points"]
        ]
        return PipelineFetchResult(
            source=self.source_key,
            summary=fetched["summary"],
            payload=fetched["payload"],
            records=records,
        )
