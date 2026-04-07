from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.ingestion.pipelines.base import BaseIngestionPipeline
from app.ingestion.types import NormalizedObservation, PipelineFetchResult

logger = logging.getLogger(__name__)

USGS_ALL_MONTH_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson"


def parse_usgs_geojson(payload: dict) -> list[NormalizedObservation]:
    records: list[NormalizedObservation] = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or [None, None, None]
        timestamp_ms = properties.get("time")
        if not timestamp_ms:
            continue
        observed_at = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()
        magnitude = properties.get("mag")
        records.append(
            NormalizedObservation(
                source="usgs_earthquakes",
                metric="earthquake_magnitude",
                timestamp=observed_at,
                value=magnitude,
                metadata={
                    "label": "Earthquake magnitude",
                    "place": properties.get("place"),
                    "event_id": feature.get("id"),
                    "detail_url": properties.get("url"),
                    "longitude": coordinates[0],
                    "latitude": coordinates[1],
                    "depth_km": coordinates[2],
                    "significance": properties.get("sig"),
                    "felt_reports": properties.get("felt"),
                    "tsunami": properties.get("tsunami"),
                    "source_url": USGS_ALL_MONTH_URL,
                    "unit": "Mw",
                },
            )
        )
    return records


class USGSEarthquakePipeline(BaseIngestionPipeline):
    source_key = "usgs_earthquakes"
    label = "USGS Earthquake Feed"

    def fetch(self, **kwargs) -> PipelineFetchResult:
        logger.info("Fetching USGS earthquake geojson feed")
        response = httpx.get(USGS_ALL_MONTH_URL, timeout=30)
        response.raise_for_status()
        payload = response.json()
        records = parse_usgs_geojson(payload)
        latest = records[-1] if records else None
        summary = "USGS earthquake feed fetched"
        if latest:
            summary = f"USGS earthquake feed through {latest.timestamp} with {len(records)} events"
        return PipelineFetchResult(
            source=self.source_key,
            summary=summary,
            payload={
                "source_url": USGS_ALL_MONTH_URL,
                "record_count": len(records),
            },
            records=records,
        )
