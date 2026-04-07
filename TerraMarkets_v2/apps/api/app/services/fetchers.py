from __future__ import annotations

from datetime import datetime, timezone

import httpx


def fetch_open_meteo_current(latitude: float, longitude: float, label: str) -> dict:
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,wind_speed_10m,precipitation",
            "timezone": "UTC",
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    current = payload.get("current", {})
    observed_at = current.get("time")
    if not observed_at:
        observed_at = datetime.now(timezone.utc).isoformat()

    return {
        "summary": f"Current Open-Meteo observation for {label}",
        "payload": payload,
        "points": [
            {
                "series_key": "temperature_2m",
                "label": f"{label} temperature",
                "numeric_value": current.get("temperature_2m"),
                "unit": payload.get("current_units", {}).get("temperature_2m"),
                "observed_at": observed_at,
                "metadata_json": {"latitude": latitude, "longitude": longitude},
            },
            {
                "series_key": "wind_speed_10m",
                "label": f"{label} wind speed",
                "numeric_value": current.get("wind_speed_10m"),
                "unit": payload.get("current_units", {}).get("wind_speed_10m"),
                "observed_at": observed_at,
                "metadata_json": {"latitude": latitude, "longitude": longitude},
            },
            {
                "series_key": "precipitation",
                "label": f"{label} precipitation",
                "numeric_value": current.get("precipitation"),
                "unit": payload.get("current_units", {}).get("precipitation"),
                "observed_at": observed_at,
                "metadata_json": {"latitude": latitude, "longitude": longitude},
            },
        ],
    }
