from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

import httpx

from app.ingestion.pipelines.base import BaseIngestionPipeline
from app.ingestion.types import NormalizedObservation, PipelineFetchResult

logger = logging.getLogger(__name__)

NOAA_CPC_ONI_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/ensostuff/ONI_v5.php"
NOAA_CPC_RONI_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/"
SEASON_TO_MONTH = {
    "DJF": 1,
    "JFM": 2,
    "FMA": 3,
    "MAM": 4,
    "AMJ": 5,
    "MJJ": 6,
    "JJA": 7,
    "JAS": 8,
    "ASO": 9,
    "SON": 10,
    "OND": 11,
    "NDJ": 12,
}
SEASON_HEADERS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]


class SimpleTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_td = False
        self.current_cell: list[str] = []
        self.current_row: list[str] = []
        self.rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"td", "th"}:
            self.in_td = True
            self.current_cell = []
        elif tag == "tr":
            self.current_row = []

    def handle_data(self, data):
        if self.in_td:
            self.current_cell.append(data)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.in_td:
            self.current_row.append("".join(self.current_cell).strip())
            self.in_td = False
        elif tag == "tr" and self.current_row:
            self.rows.append(self.current_row)


def _records_from_rows(rows: list[list[str]], *, metric: str, label: str, source_url: str) -> list[NormalizedObservation]:
    season_headers = None
    record_map: dict[str, NormalizedObservation] = {}
    for row in rows:
        upper_row = [cell.upper() for cell in row]
        if season_headers is None and len(row) >= 13 and "DJF" in upper_row and "NDJ" in upper_row:
            season_headers = upper_row[1:13]
            continue
        if season_headers is None:
            continue
        try:
            year = int(row[0])
        except (ValueError, TypeError):
            continue
        for season, value_text in zip(season_headers, row[1:13]):
            try:
                metric_value = float(value_text)
            except (TypeError, ValueError):
                continue
            month = SEASON_TO_MONTH.get(season)
            if not month:
                continue
            observed_at = datetime(year, month, 1, tzinfo=timezone.utc).isoformat()
            record_map[observed_at] = NormalizedObservation(
                source="noaa_cpc_enso",
                metric=metric,
                timestamp=observed_at,
                value=metric_value,
                metadata={
                    "label": label,
                    "season": season,
                    "unit": "index",
                    "source_url": source_url,
                },
            )
    return [record_map[key] for key in sorted(record_map.keys())]


def _extract_rows_from_plain_text(text: str) -> list[list[str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_index = None
    for index, line in enumerate(lines):
        upper = line.upper()
        if upper.startswith("YEAR") and all(header in upper for header in ("DJF", "NDJ")):
            header_index = index
            break

    if header_index is None:
        return []

    rows = [["YEAR", *SEASON_HEADERS]]
    for line in lines[header_index + 1 :]:
        year_match = re.match(r"^(\d{4})\s+(.*)$", line)
        if not year_match:
            continue
        year = year_match.group(1)
        values = re.findall(r"[-+]?\d+(?:\.\d+)?", year_match.group(2))
        if len(values) < 12:
            continue
        rows.append([year, *values[:12]])
    return rows


def parse_oni_html_table(html_text: str, *, metric: str = "oni_index", label: str = "Oceanic Nino Index", source_url: str = NOAA_CPC_ONI_URL) -> list[NormalizedObservation]:
    parser = SimpleTableParser()
    parser.feed(html_text)

    records = _records_from_rows(parser.rows, metric=metric, label=label, source_url=source_url)
    if not records:
        records = _records_from_rows(
            _extract_rows_from_plain_text(html_text),
            metric=metric,
            label=label,
            source_url=source_url,
        )

    if not records:
        raise ValueError("No ENSO observations parsed from NOAA CPC table.")
    return records


class EnsoONIPipeline(BaseIngestionPipeline):
    source_key = "enso_oni"
    label = "ENSO Oceanic Nino Index"

    def fetch(self, **kwargs) -> PipelineFetchResult:
        sources = [
            (NOAA_CPC_ONI_URL, "oni_index", "Oceanic Nino Index"),
            (NOAA_CPC_RONI_URL, "roni_index", "Relative Oceanic Nino Index"),
        ]

        last_error = None
        records: list[NormalizedObservation] | None = None
        selected_url = None
        selected_label = None
        selected_metric = None

        for url, metric, label in sources:
            try:
                logger.info("Fetching ENSO table from %s", url)
                response = httpx.get(url, timeout=20, follow_redirects=True)
                response.raise_for_status()
                records = parse_oni_html_table(response.text, metric=metric, label=label, source_url=url)
                selected_url = url
                selected_label = label
                selected_metric = metric
                break
            except Exception as exc:
                logger.warning("ENSO fetch failed for %s: %s", url, exc)
                last_error = exc

        if not records or not selected_url or not selected_label or not selected_metric:
            raise ValueError(f"Unable to fetch ENSO table from NOAA CPC: {last_error}")

        latest = records[-1]
        return PipelineFetchResult(
            source=self.source_key,
            summary=f"NOAA CPC {selected_label} table through {latest.timestamp} at {latest.value}",
            payload={
                "source_url": selected_url,
                "metric": selected_metric,
                "record_count": len(records),
            },
            records=records,
        )
