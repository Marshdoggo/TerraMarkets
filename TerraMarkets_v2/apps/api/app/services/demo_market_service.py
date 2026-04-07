from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.market import Market
from app.models.market_data_link import MarketDataLink
from app.models.user import User
from app.services.trading_service import record_market_snapshot


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


DEMO_MARKET_CATALOG = {
    "nsidc_charctic_daily": {
        "pipeline_label": "Arctic sea ice",
        "markets": [
            {
                "market": {
                    "slug": "arctic-sea-ice-minimum-2026",
                    "title": "Will September 2026 Arctic sea ice extent fall below 4.0 million sq km?",
                    "category": "arctic systems",
                    "description": "Flagship Arctic market tied to the NSIDC Charctic daily extent dataset.",
                    "resolution_criteria": "Resolve YES if the NSIDC Charctic reference dataset reports the September 2026 monthly average extent below 4.0 million square kilometers.",
                    "close_at_offset_days": 60,
                    "outcomes": ["YES", "NO"],
                    "b": 90,
                },
                "link": {
                    "source_key": "nsidc_charctic_daily",
                    "series_key": "daily_extent_million_sq_km",
                    "label": "NSIDC Arctic sea ice extent",
                    "notes": "Daily Arctic sea ice extent from NSIDC Charctic (north hemisphere daily extent file).",
                },
            },
            {
                "market": {
                    "slug": "arctic-sea-ice-minimum-vs-2025",
                    "title": "Will the September 2026 Arctic sea ice minimum finish below the September 2025 minimum?",
                    "category": "arctic systems",
                    "description": "Compares the next September minimum against the latest observed September benchmark.",
                    "resolution_criteria": "Resolve YES if the NSIDC Charctic September 2026 monthly average extent is lower than the NSIDC Charctic September 2025 monthly average extent.",
                    "close_at_offset_days": 75,
                    "outcomes": ["YES", "NO"],
                    "b": 75,
                },
                "link": {
                    "source_key": "nsidc_charctic_daily",
                    "series_key": "daily_extent_million_sq_km",
                    "label": "NSIDC Arctic sea ice extent",
                    "notes": "Daily Arctic sea ice extent from NSIDC Charctic (north hemisphere daily extent file).",
                },
            },
            {
                "market": {
                    "slug": "arctic-sea-ice-below-5m-before-august",
                    "title": "Will Arctic sea ice extent first fall below 5.0 million sq km before August 15, 2026?",
                    "category": "arctic systems",
                    "description": "Event-timing market based on the seasonal pace of Arctic melt.",
                    "resolution_criteria": "Resolve YES if the NSIDC Charctic daily extent dataset records a daily Arctic extent below 5.0 million square kilometers on or before August 15, 2026.",
                    "close_at_offset_days": 90,
                    "outcomes": ["YES", "NO"],
                    "b": 60,
                },
                "link": {
                    "source_key": "nsidc_charctic_daily",
                    "series_key": "daily_extent_million_sq_km",
                    "label": "NSIDC Arctic sea ice extent",
                    "notes": "Daily Arctic sea ice extent from NSIDC Charctic (north hemisphere daily extent file).",
                },
            },
        ],
    },
    "enso_oni": {
        "pipeline_label": "ENSO / ONI",
        "markets": [
            {
                "market": {
                    "slug": "enso-oni-above-1-next-release",
                    "title": "Will the next NOAA ONI reading print above +1.0?",
                    "category": "enso outlook",
                    "description": "Tracks whether the next published Oceanic Nino Index crosses strong El Nino territory.",
                    "resolution_criteria": "Resolve YES if the next NOAA CPC ONI table release reports the most recent ONI value above +1.0.",
                    "close_at_offset_days": 45,
                    "outcomes": ["YES", "NO"],
                    "b": 55,
                },
                "link": {
                    "source_key": "enso_oni",
                    "series_key": "oni_index",
                    "label": "Oceanic Nino Index",
                    "notes": "NOAA CPC Oceanic Nino Index monthly series.",
                },
            },
            {
                "market": {
                    "slug": "enso-oni-positive-through-quarter",
                    "title": "Will ONI stay positive through the next full quarter?",
                    "category": "enso outlook",
                    "description": "Tests whether ENSO remains on the warm side through the next three-month window.",
                    "resolution_criteria": "Resolve YES if all ONI values published for the next full quarter remain above 0.0.",
                    "close_at_offset_days": 75,
                    "outcomes": ["YES", "NO"],
                    "b": 60,
                },
                "link": {
                    "source_key": "enso_oni",
                    "series_key": "oni_index",
                    "label": "Oceanic Nino Index",
                    "notes": "NOAA CPC Oceanic Nino Index monthly series.",
                },
            },
            {
                "market": {
                    "slug": "enso-roni-negative-next-update",
                    "title": "Will the next Relative ONI update come in below 0.0?",
                    "category": "enso outlook",
                    "description": "Companion ENSO market using the relative ONI series instead of the standard ONI line.",
                    "resolution_criteria": "Resolve YES if the next NOAA CPC Relative ONI release reports the newest RONI value below 0.0.",
                    "close_at_offset_days": 60,
                    "outcomes": ["YES", "NO"],
                    "b": 50,
                },
                "link": {
                    "source_key": "enso_oni",
                    "series_key": "roni_index",
                    "label": "Relative Oceanic Nino Index",
                    "notes": "NOAA CPC Relative ONI monthly series.",
                },
            },
        ],
    },
    "usgs_earthquakes": {
        "pipeline_label": "USGS earthquakes",
        "markets": [
            {
                "market": {
                    "slug": "earthquake-m7-this-month",
                    "title": "Will the USGS monthly feed record a magnitude 7.0+ earthquake this month?",
                    "category": "earthquakes",
                    "description": "Threshold market on whether a major quake appears in the live monthly USGS feed.",
                    "resolution_criteria": "Resolve YES if the USGS all-month earthquake feed contains at least one event with magnitude 7.0 or higher before this market closes.",
                    "close_at_offset_days": 30,
                    "outcomes": ["YES", "NO"],
                    "b": 70,
                },
                "link": {
                    "source_key": "usgs_earthquakes",
                    "series_key": "earthquake_magnitude",
                    "label": "Earthquake magnitude",
                    "notes": "USGS all-month earthquake feed magnitudes.",
                },
            },
            {
                "market": {
                    "slug": "earthquake-m6-pacific-week",
                    "title": "Will the next week include a magnitude 6.0+ quake in the USGS feed?",
                    "category": "earthquakes",
                    "description": "Short-duration activity market using the latest USGS event stream.",
                    "resolution_criteria": "Resolve YES if the USGS earthquake feed records at least one magnitude 6.0 or greater event before this market closes.",
                    "close_at_offset_days": 14,
                    "outcomes": ["YES", "NO"],
                    "b": 45,
                },
                "link": {
                    "source_key": "usgs_earthquakes",
                    "series_key": "earthquake_magnitude",
                    "label": "Earthquake magnitude",
                    "notes": "USGS all-month earthquake feed magnitudes.",
                },
            },
            {
                "market": {
                    "slug": "earthquake-max-mag-above-68",
                    "title": "Will the strongest quake in the current feed window exceed magnitude 6.8?",
                    "category": "earthquakes",
                    "description": "A max-intensity market based on the strongest event in the rolling monthly feed.",
                    "resolution_criteria": "Resolve YES if the maximum earthquake magnitude observed in the USGS all-month feed before close exceeds 6.8.",
                    "close_at_offset_days": 35,
                    "outcomes": ["YES", "NO"],
                    "b": 58,
                },
                "link": {
                    "source_key": "usgs_earthquakes",
                    "series_key": "earthquake_magnitude",
                    "label": "Earthquake magnitude",
                    "notes": "USGS all-month earthquake feed magnitudes.",
                },
            },
        ],
    },
    "nasa_donki_solar_flares": {
        "pipeline_label": "NASA DONKI solar flares",
        "markets": [
            {
                "market": {
                    "slug": "solar-flare-m-class-next-30d",
                    "title": "Will NASA DONKI log an M-class-or-higher solar flare in the next 30 days?",
                    "category": "solar flares",
                    "description": "Threshold flare market tied to the rolling DONKI solar flare feed.",
                    "resolution_criteria": "Resolve YES if NASA DONKI records a solar flare with intensity 1.0 or greater in the linked series before this market closes.",
                    "close_at_offset_days": 30,
                    "outcomes": ["YES", "NO"],
                    "b": 52,
                },
                "link": {
                    "source_key": "nasa_donki_solar_flares",
                    "series_key": "solar_flare_intensity",
                    "label": "Solar flare intensity",
                    "notes": "NASA DONKI solar flare intensity feed.",
                },
            },
            {
                "market": {
                    "slug": "solar-flare-x-class-this-quarter",
                    "title": "Will an X-class solar flare appear in the DONKI feed this quarter?",
                    "category": "solar flares",
                    "description": "Captures rare high-intensity flare risk over a longer horizon.",
                    "resolution_criteria": "Resolve YES if NASA DONKI records any solar flare with intensity 10.0 or greater before this market closes.",
                    "close_at_offset_days": 90,
                    "outcomes": ["YES", "NO"],
                    "b": 68,
                },
                "link": {
                    "source_key": "nasa_donki_solar_flares",
                    "series_key": "solar_flare_intensity",
                    "label": "Solar flare intensity",
                    "notes": "NASA DONKI solar flare intensity feed.",
                },
            },
            {
                "market": {
                    "slug": "solar-flare-repeat-m-events",
                    "title": "Will the DONKI feed record at least two notable flare events before close?",
                    "category": "solar flares",
                    "description": "Frequency-oriented flare market using repeated DONKI detections.",
                    "resolution_criteria": "Resolve YES if at least two solar flare observations with numeric intensity values are recorded by NASA DONKI before this market closes.",
                    "close_at_offset_days": 45,
                    "outcomes": ["YES", "NO"],
                    "b": 48,
                },
                "link": {
                    "source_key": "nasa_donki_solar_flares",
                    "series_key": "solar_flare_intensity",
                    "label": "Solar flare intensity",
                    "notes": "NASA DONKI solar flare intensity feed.",
                },
            },
        ],
    },
}


def _materialize_market_entry(entry: dict) -> dict:
    payload = deepcopy(entry)
    market_payload = payload["market"]
    offset_days = market_payload.pop("close_at_offset_days")
    market_payload["close_at"] = utc_now() + timedelta(days=offset_days)
    return payload


def build_demo_market_entries() -> list[dict]:
    entries: list[dict] = []
    for source_key, bundle in DEMO_MARKET_CATALOG.items():
        for item in bundle["markets"]:
            materialized = _materialize_market_entry(item)
            materialized["source_key"] = source_key
            materialized["pipeline_label"] = bundle["pipeline_label"]
            entries.append(materialized)
    return entries


def seed_demo_markets(db: Session) -> dict:
    admin = db.scalar(select(User).order_by(User.id.asc()))
    if not admin:
        raise RuntimeError("No users available. Seed admin first.")

    results: dict[str, dict] = {
        source_key: {
            "source_key": source_key,
            "pipeline_label": bundle["pipeline_label"],
            "created_markets": 0,
            "existing_markets": 0,
            "created_links": 0,
            "existing_links": 0,
        }
        for source_key, bundle in DEMO_MARKET_CATALOG.items()
    }

    for entry in build_demo_market_entries():
        market_payload = entry["market"]
        link_payload = entry["link"]
        source_key = entry["source_key"]
        summary = results[source_key]

        existing_market = db.scalar(select(Market).where(Market.slug == market_payload["slug"]))
        if existing_market:
            market = existing_market
            summary["existing_markets"] += 1
        else:
            market = Market(
                created_by_user_id=admin.id,
                q={outcome: 0.0 for outcome in market_payload["outcomes"]},
                **market_payload,
            )
            db.add(market)
            db.flush()
            record_market_snapshot(db, market=market, event_type="create")
            summary["created_markets"] += 1

        existing_link = db.scalar(
            select(MarketDataLink).where(
                MarketDataLink.market_id == market.id,
                MarketDataLink.source_key == link_payload["source_key"],
                MarketDataLink.series_key == link_payload["series_key"],
            )
        )
        if existing_link:
            summary["existing_links"] += 1
        else:
            db.add(MarketDataLink(market_id=market.id, **link_payload))
            summary["created_links"] += 1

    return {
        "created_markets": sum(item["created_markets"] for item in results.values()),
        "existing_markets": sum(item["existing_markets"] for item in results.values()),
        "created_links": sum(item["created_links"] for item in results.values()),
        "existing_links": sum(item["existing_links"] for item in results.values()),
        "pipelines": list(results.values()),
    }
