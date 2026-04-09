from __future__ import annotations

import logging
import re
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser

import httpx

from app.ingestion.pipelines.base import BaseIngestionPipeline
from app.ingestion.types import NormalizedObservation, PipelineFetchResult

logger = logging.getLogger(__name__)

SMITHSONIAN_WEEKLY_VOLCANO_URL = "https://volcano.si.edu/reports_weekly.cfm"
SMITHSONIAN_WEEKSTART_PARAM = "weekstart"
WEEKLY_REPORT_HEADER_RE = re.compile(
    r"Weekly Volcanic Activity Report for the week of\s+(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s*[-–—]\s*(\d{1,2})\s+"
    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
    r"(\d{4})",
    re.IGNORECASE,
)


class WeeklyVolcanoTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_cell = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th"}:
            self.in_cell = True
            self.current_cell = []
        elif tag == "tr":
            self.current_row = []

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_cell:
            self.current_row.append("".join(self.current_cell).strip())
            self.in_cell = False
        elif tag == "tr" and self.current_row:
            self.rows.append(self.current_row)

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)


def _parse_report_timestamp(html_text: str) -> str:
    weekly_match = WEEKLY_REPORT_HEADER_RE.search(html_text)
    if weekly_match:
        end_day = int(weekly_match.group(3))
        end_month = weekly_match.group(4)
        year = int(weekly_match.group(5))
        parsed = datetime.strptime(f"{end_day} {end_month} {year}", "%d %B %Y").replace(tzinfo=timezone.utc)
        return parsed.isoformat()

    month_match = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",
        html_text,
        re.IGNORECASE,
    )
    if month_match:
        try:
            parsed = datetime.strptime(month_match.group(0), "%B %d, %Y").replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except ValueError:
            pass

    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", html_text)
    if iso_match:
        return datetime.fromisoformat(f"{iso_match.group(1)}T00:00:00+00:00").isoformat()
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def _parse_report_weekstart_date(html_text: str) -> date:
    weekly_match = WEEKLY_REPORT_HEADER_RE.search(html_text)
    if not weekly_match:
        return datetime.now(timezone.utc).date()
    start_day = int(weekly_match.group(1))
    start_month = weekly_match.group(2)
    end_day = int(weekly_match.group(3))
    end_month = weekly_match.group(4)
    year = int(weekly_match.group(5))
    end_date = datetime.strptime(f"{end_day} {end_month} {year}", "%d %B %Y").date()
    start_date = datetime.strptime(f"{start_day} {start_month} {year}", "%d %B %Y").date()
    if start_date > end_date:
        start_date = datetime.strptime(f"{start_day} {start_month} {year - 1}", "%d %B %Y").date()
    return start_date


def parse_smithsonian_weekly_report(html_text: str) -> list[NormalizedObservation]:
    parser = WeeklyVolcanoTableParser()
    parser.feed(html_text)
    rows = parser.rows
    header_index = None
    for index, row in enumerate(rows):
        lowered = [cell.lower() for cell in row]
        if (
            any(cell in {"name", "volcano"} or "volcano" in cell for cell in lowered)
            and (
                any("activity" in cell or "summary" in cell for cell in lowered)
                or any("report type" in cell for cell in lowered)
            )
        ):
            header_index = index
            break

    volcano_rows: list[dict] = []
    if header_index is not None:
        header = [cell.strip().lower() for cell in rows[header_index]]
        expected_width = len(header)
        for row in rows[header_index + 1 :]:
            if len(row) < 2:
                continue
            if any(cell.lower().startswith("copyright") for cell in row):
                break
            if len(row) != expected_width:
                break
            row_map = {}
            for key, value in zip(header, row):
                row_map[key] = value.strip()
            volcano_name = (row_map.get("name") or row_map.get("volcano") or row[0]).strip()
            activity_summary = (
                row_map.get("activity summary")
                or row_map.get("report type")
                or " ".join(row[1:]).strip()
            )
            if not volcano_name or volcano_name.lower() == "volcano":
                continue
            if volcano_name.lower() in {"weekly report", "archive", "feeds", "criteria & disclaimers", "acronyms & abbreviations"}:
                break
            volcano_rows.append(
                {
                    "name": volcano_name,
                    "activity_summary": activity_summary,
                    "country": row_map.get("country"),
                    "volcanic_region": row_map.get("volcanic region"),
                    "eruption_start_date": row_map.get("eruption start date"),
                    "report_type": row_map.get("report type"),
                }
            )

    observed_at = _parse_report_timestamp(html_text)
    if not volcano_rows:
        if not WEEKLY_REPORT_HEADER_RE.search(html_text):
            raise ValueError("No volcanic activity rows parsed from Smithsonian weekly report.")
        return [
            NormalizedObservation(
                source="smithsonian_volcanoes",
                metric="weekly_eruption_count",
                timestamp=observed_at,
                value=0,
                metadata={
                    "label": "Weekly eruption count",
                    "unit": "volcanoes",
                    "source_url": SMITHSONIAN_WEEKLY_VOLCANO_URL,
                    "sample_volcanoes": [],
                    "report_types": [],
                    "empty_report": True,
                },
            ),
            NormalizedObservation(
                source="smithsonian_volcanoes",
                metric="active_volcano_count",
                timestamp=observed_at,
                value=0,
                metadata={
                    "label": "Active volcano count",
                    "unit": "volcanoes",
                    "source_url": SMITHSONIAN_WEEKLY_VOLCANO_URL,
                    "sample_volcanoes": [],
                    "report_types": [],
                    "empty_report": True,
                },
            ),
        ]

    eruption_count = len(volcano_rows)
    active_count = len(
        [
            row
            for row in volcano_rows
            if not any(term in (row["activity_summary"] or "").lower() for term in ("no eruption", "unrest only", "declining"))
        ]
    )
    active_count = active_count or eruption_count
    sample_names = [row["name"] for row in volcano_rows[:8]]
    report_types = sorted({row.get("report_type") for row in volcano_rows if row.get("report_type")})

    return [
        NormalizedObservation(
            source="smithsonian_volcanoes",
            metric="weekly_eruption_count",
            timestamp=observed_at,
            value=eruption_count,
            metadata={
                "label": "Weekly eruption count",
                "unit": "volcanoes",
                "source_url": SMITHSONIAN_WEEKLY_VOLCANO_URL,
                "sample_volcanoes": sample_names,
                "report_types": report_types,
            },
        ),
        NormalizedObservation(
            source="smithsonian_volcanoes",
            metric="active_volcano_count",
            timestamp=observed_at,
            value=active_count,
            metadata={
                "label": "Active volcano count",
                "unit": "volcanoes",
                "source_url": SMITHSONIAN_WEEKLY_VOLCANO_URL,
                "sample_volcanoes": sample_names,
                "report_types": report_types,
            },
        ),
    ]


class SmithsonianVolcanoPipeline(BaseIngestionPipeline):
    source_key = "smithsonian_volcanoes"
    label = "Smithsonian Weekly Volcano Activity"

    def fetch(self, **kwargs) -> PipelineFetchResult:
        logger.info("Fetching Smithsonian weekly volcanic activity report")
        response = httpx.get(SMITHSONIAN_WEEKLY_VOLCANO_URL, timeout=30, follow_redirects=True)
        response.raise_for_status()
        records = parse_smithsonian_weekly_report(response.text)
        latest = records[0]
        return PipelineFetchResult(
            source=self.source_key,
            summary=f"Smithsonian weekly volcanic activity through {latest.timestamp} across {int(records[0].value)} erupting volcanoes",
            payload={
                "source_url": SMITHSONIAN_WEEKLY_VOLCANO_URL,
                "record_count": len(records),
                "eruption_count": int(records[0].value),
                "active_count": int(records[1].value),
            },
            records=records,
        )


def fetch_smithsonian_weekly_report_for_weekstart(weekstart: date) -> PipelineFetchResult:
    response = httpx.get(
        SMITHSONIAN_WEEKLY_VOLCANO_URL,
        params={SMITHSONIAN_WEEKSTART_PARAM: weekstart.strftime("%Y%m%d")},
        timeout=30,
        follow_redirects=True,
    )
    response.raise_for_status()
    records = parse_smithsonian_weekly_report(response.text)
    latest = records[0]
    return PipelineFetchResult(
        source="smithsonian_volcanoes",
        summary=f"Smithsonian weekly volcanic activity through {latest.timestamp} across {int(records[0].value)} erupting volcanoes",
        payload={
            "source_url": f"{SMITHSONIAN_WEEKLY_VOLCANO_URL}?{SMITHSONIAN_WEEKSTART_PARAM}={weekstart.strftime('%Y%m%d')}",
            "record_count": len(records),
            "eruption_count": int(records[0].value),
            "active_count": int(records[1].value),
            "requested_weekstart": weekstart.isoformat(),
            "report_weekstart": _parse_report_weekstart_date(response.text).isoformat(),
        },
        records=records,
    )


def fetch_smithsonian_weekly_history(*, weeks: int = 26) -> PipelineFetchResult:
    response = httpx.get(SMITHSONIAN_WEEKLY_VOLCANO_URL, timeout=30, follow_redirects=True)
    response.raise_for_status()
    current_html = response.text
    current_weekstart = _parse_report_weekstart_date(current_html)
    aggregated: dict[tuple[str, str], NormalizedObservation] = {}
    visited_weekstarts: list[str] = []
    skipped_weekstarts: list[str] = []

    for offset in range(max(weeks, 1)):
        requested_weekstart = current_weekstart - timedelta(days=7 * offset)
        try:
            result = fetch_smithsonian_weekly_report_for_weekstart(requested_weekstart)
        except Exception as exc:
            logger.warning(
                "Skipping Smithsonian weekly archive report for %s: %s",
                requested_weekstart.isoformat(),
                exc,
            )
            skipped_weekstarts.append(requested_weekstart.isoformat())
            continue
        visited_weekstarts.append(result.payload.get("report_weekstart") or requested_weekstart.isoformat())
        for record in result.records:
            aggregated[(record.metric, record.timestamp)] = record

    if not aggregated:
        raise ValueError("No Smithsonian weekly archive reports could be parsed for backfill.")
    ordered_records = [aggregated[key] for key in sorted(aggregated.keys(), key=lambda item: item[1])]
    latest = ordered_records[-1]
    return PipelineFetchResult(
        source="smithsonian_volcanoes",
        summary=f"Smithsonian weekly volcanic history backfill through {latest.timestamp} across {len(ordered_records) // 2} weeks",
        payload={
            "source_url": SMITHSONIAN_WEEKLY_VOLCANO_URL,
            "record_count": len(ordered_records),
            "weeks_requested": weeks,
            "weeks_backfilled": len({record.timestamp for record in ordered_records}),
            "visited_weekstarts": visited_weekstarts,
            "skipped_weekstarts": skipped_weekstarts,
        },
        records=ordered_records,
    )
