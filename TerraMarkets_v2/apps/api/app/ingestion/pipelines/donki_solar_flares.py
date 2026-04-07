from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.ingestion.pipelines.base import BaseIngestionPipeline
from app.ingestion.types import NormalizedObservation, PipelineFetchResult

logger = logging.getLogger(__name__)

NASA_DONKI_FLR_URL = "https://api.nasa.gov/DONKI/FLR"


def parse_flare_intensity(class_type: str | None) -> tuple[str | None, float | None]:
    if not class_type:
        return None, None
    flare_class = class_type[:1]
    try:
        intensity = float(class_type[1:])
    except ValueError:
        intensity = None
    return flare_class, intensity


def normalize_donki_flares(payload: list[dict]) -> list[NormalizedObservation]:
    records: list[NormalizedObservation] = []
    for event in payload:
        begin_time = event.get("beginTime")
        if not begin_time:
            continue
        flare_class, intensity = parse_flare_intensity(event.get("classType"))
        records.append(
            NormalizedObservation(
                source="nasa_donki_solar_flares",
                metric="solar_flare_intensity",
                timestamp=datetime.fromisoformat(begin_time.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat(),
                value=intensity,
                metadata={
                    "label": "Solar flare intensity",
                    "flare_class": flare_class,
                    "class_type": event.get("classType"),
                    "source_location": event.get("sourceLocation"),
                    "peak_time": event.get("peakTime"),
                    "end_time": event.get("endTime"),
                    "active_region": event.get("activeRegionNum"),
                    "linked_events": event.get("linkedEvents") or [],
                    "source_url": NASA_DONKI_FLR_URL,
                    "unit": "flare class magnitude",
                },
            )
        )
    return records


class DonkiSolarFlarePipeline(BaseIngestionPipeline):
    source_key = "nasa_donki_solar_flares"
    label = "NASA DONKI Solar Flares"

    def fetch(self, *, start_date: str | None = None, end_date: str | None = None, **kwargs) -> PipelineFetchResult:
        if not settings.NASA_DONKI_API_KEY:
            raise ValueError("NASA_DONKI_API_KEY is not configured.")

        end = date.fromisoformat(end_date) if end_date else date.today()
        start = date.fromisoformat(start_date) if start_date else end - timedelta(days=365)

        logger.info("Fetching NASA DONKI solar flares from %s to %s", start, end)
        response = httpx.get(
            NASA_DONKI_FLR_URL,
            params={
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "api_key": settings.NASA_DONKI_API_KEY,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        records = normalize_donki_flares(payload)
        latest = records[-1] if records else None
        summary = f"NASA DONKI solar flare feed from {start.isoformat()} to {end.isoformat()}"
        if latest:
            summary = f"NASA DONKI solar flares through {latest.timestamp} with {len(records)} events"
        return PipelineFetchResult(
            source=self.source_key,
            summary=summary,
            payload={
                "source_url": NASA_DONKI_FLR_URL,
                "record_count": len(records),
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            records=records,
        )
