from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO

import httpx

NSIDC_CHARCTIC_DAILY_URL = "https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv"


def parse_nsidc_daily_extent_csv(csv_text: str, *, days: int = 60) -> list[dict]:
    header_index = None
    lines = csv_text.splitlines()
    for index, line in enumerate(lines):
        normalized = line.strip().lstrip("\ufeff").lower()
        if normalized.startswith("year") and "extent" in normalized:
            header_index = index
            break

    if header_index is None:
        raise ValueError("Unable to locate NSIDC daily extent header row.")

    reader = csv.DictReader(StringIO("\n".join(lines[header_index:])))
    if reader.fieldnames:
        reader.fieldnames = [
            field.strip().lstrip("\ufeff").lower().replace(" ", "_")
            for field in reader.fieldnames
        ]
    points: list[dict] = []
    for row in reader:
        if not row:
            continue
        normalized_row = {
            (key.strip().lower().replace(" ", "_") if isinstance(key, str) else key): value
            for key, value in row.items()
        }
        try:
            year = int((normalized_row.get("year") or "").strip())
            month = int((normalized_row.get("month") or "").strip())
            day = int((normalized_row.get("day") or "").strip())
            extent_raw = (
                normalized_row.get("extent")
                or normalized_row.get("sea_ice_extent")
                or normalized_row.get("ice_extent")
                or ""
            )
            extent = float(extent_raw.strip())
        except (TypeError, ValueError):
            continue

        observed_at = datetime(year, month, day, tzinfo=timezone.utc)
        points.append(
            {
                "series_key": "daily_extent_million_sq_km",
                "label": "Arctic sea ice extent",
                "numeric_value": extent,
                "unit": "million sq km",
                "observed_at": observed_at.isoformat(),
                "metadata_json": {
                    "source": "nsidc_charctic",
                    "dataset": "G02135",
                    "hemisphere": "north",
                },
            }
        )

    if not points:
        raise ValueError("No Arctic extent points parsed from NSIDC daily file.")

    return points[-days:]


def fetch_nsidc_charctic_daily(*, days: int = 60, source_key: str = "nsidc_charctic_daily") -> dict:
    response = httpx.get(NSIDC_CHARCTIC_DAILY_URL, timeout=30)
    response.raise_for_status()
    points = parse_nsidc_daily_extent_csv(response.text, days=days)
    latest = points[-1]

    return {
        "summary": (
            f"NSIDC Charctic Arctic sea ice extent through {latest['observed_at']} "
            f"at {latest['numeric_value']} {latest['unit']}"
        ),
        "payload": {
            "source_url": NSIDC_CHARCTIC_DAILY_URL,
            "point_count": len(points),
            "days_requested": days,
            "latest_series_key": latest["series_key"],
        },
        "points": points,
        "source_key": source_key,
    }
