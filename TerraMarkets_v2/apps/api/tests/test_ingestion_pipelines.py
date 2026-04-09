from __future__ import annotations

import unittest
from unittest.mock import patch

from app.ingestion.pipelines.smithsonian_volcanoes import (
    fetch_smithsonian_weekly_history,
    parse_smithsonian_weekly_report,
)
from app.ingestion.types import NormalizedObservation, PipelineFetchResult
from app.ingestion.pipelines.donki_solar_flares import normalize_donki_flares
from app.ingestion.pipelines.enso_oni import parse_oni_html_table
from app.ingestion.pipelines.usgs_earthquakes import parse_usgs_geojson
from app.oracles.nsidc_charctic import parse_nsidc_daily_extent_csv


SAMPLE_ONI_HTML = """
<html>
  <body>
    <table>
      <tr>
        <th>Year</th><th>DJF</th><th>JFM</th><th>FMA</th><th>MAM</th><th>AMJ</th><th>MJJ</th>
        <th>JJA</th><th>JAS</th><th>ASO</th><th>SON</th><th>OND</th><th>NDJ</th>
      </tr>
      <tr>
        <td>2025</td><td>-0.8</td><td>-0.6</td><td>-0.4</td><td>-0.2</td><td>0.0</td><td>0.2</td>
        <td>0.4</td><td>0.5</td><td>0.7</td><td>0.8</td><td>1.0</td><td>1.1</td>
      </tr>
    </table>
  </body>
</html>
"""

SAMPLE_RONI_TEXT = """
Updated on March 2026
YEAR DJF JFM FMA MAM AMJ MJJ JJA JAS ASO SON OND NDJ
2025 -0.8 -0.6 -0.4 -0.2 0.0 0.2 0.4 0.5 0.7 0.8 1.0 1.1
"""

SAMPLE_USGS_PAYLOAD = {
    "features": [
        {
            "id": "abcd1234",
            "properties": {
                "mag": 5.4,
                "place": "123 km SW of Sample City",
                "time": 1773705600000,
                "url": "https://example.com/event",
                "sig": 447,
                "felt": 12,
                "tsunami": 0,
            },
            "geometry": {"coordinates": [-149.9, 61.2, 33.1]},
        }
    ]
}

SAMPLE_DONKI_PAYLOAD = [
    {
        "beginTime": "2026-03-15T12:30Z",
        "peakTime": "2026-03-15T12:34Z",
        "endTime": "2026-03-15T12:40Z",
        "classType": "M2.3",
        "sourceLocation": "N12W34",
        "activeRegionNum": 4567,
        "linkedEvents": [{"activityID": "evt-1"}],
    }
]

SAMPLE_NSIDC_CSV = """
metadata row
Year,Month,Day,Extent
2026,03,14,2.1
2026,03,15,2.3
"""

SAMPLE_SMITHSONIAN_HTML = """
<html>
  <body>
    <h2>Weekly Report: March 15, 2026</h2>
    <table>
      <tr><th>Name</th><th>Country</th><th>Volcanic Region</th><th>Eruption Start Date</th><th>Report Type</th></tr>
      <tr><td>Kilauea</td><td>United States</td><td>Hawaii</td><td>2025-12-23</td><td>Ongoing Eruption</td></tr>
      <tr><td>Etna</td><td>Italy</td><td>Mediterranean</td><td>2026-03-01</td><td>New Activity/Unrest</td></tr>
      <tr><td>Fernandina</td><td>Ecuador</td><td>Galapagos</td><td>--</td><td>No Eruption</td></tr>
    </table>
  </body>
</html>
"""

SAMPLE_EMPTY_SMITHSONIAN_HTML = """
<html>
  <body>
    <h2>Smithsonian / USGS Weekly Volcanic Activity Report for the week of 12 March-18 March 2026</h2>
    <p>No volcanic activity met the reporting threshold this week.</p>
  </body>
</html>
"""


class IngestionPipelineTests(unittest.TestCase):
    def test_parse_oni_html_table(self):
        records = parse_oni_html_table(SAMPLE_ONI_HTML)
        self.assertEqual(len(records), 12)
        self.assertEqual(records[0].source, "noaa_cpc_enso")
        self.assertEqual(records[0].metric, "oni_index")
        self.assertEqual(records[0].value, -0.8)
        self.assertEqual(records[-1].metadata["season"], "NDJ")

    def test_parse_roni_plain_text_table(self):
        records = parse_oni_html_table(
            SAMPLE_RONI_TEXT,
            metric="roni_index",
            label="Relative Oceanic Nino Index",
            source_url="https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/",
        )
        self.assertEqual(len(records), 12)
        self.assertEqual(records[0].metric, "roni_index")
        self.assertEqual(records[0].metadata["label"], "Relative Oceanic Nino Index")
        self.assertEqual(records[-1].value, 1.1)

    def test_parse_usgs_geojson(self):
        records = parse_usgs_geojson(SAMPLE_USGS_PAYLOAD)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source, "usgs_earthquakes")
        self.assertEqual(records[0].metric, "earthquake_magnitude")
        self.assertEqual(records[0].value, 5.4)
        self.assertEqual(records[0].metadata["place"], "123 km SW of Sample City")

    def test_normalize_donki_flares(self):
        records = normalize_donki_flares(SAMPLE_DONKI_PAYLOAD)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].source, "nasa_donki_solar_flares")
        self.assertEqual(records[0].metric, "solar_flare_intensity")
        self.assertEqual(records[0].value, 2.3)
        self.assertEqual(records[0].metadata["flare_class"], "M")

    def test_parse_antarctic_nsidc_csv(self):
        points = parse_nsidc_daily_extent_csv(
            SAMPLE_NSIDC_CSV,
            days=2,
            hemisphere="south",
            label="Antarctic sea ice extent",
        )
        self.assertEqual(len(points), 2)
        self.assertEqual(points[-1]["numeric_value"], 2.3)
        self.assertEqual(points[-1]["metadata_json"]["hemisphere"], "south")

    def test_parse_smithsonian_weekly_report(self):
        records = parse_smithsonian_weekly_report(SAMPLE_SMITHSONIAN_HTML)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].source, "smithsonian_volcanoes")
        self.assertEqual(records[0].metric, "weekly_eruption_count")
        self.assertEqual(records[0].value, 3)
        self.assertEqual(records[1].metric, "active_volcano_count")
        self.assertEqual(records[1].value, 2)
        self.assertIn("Ongoing Eruption", records[0].metadata["report_types"])

    def test_parse_smithsonian_weekly_report_handles_empty_report(self):
        records = parse_smithsonian_weekly_report(SAMPLE_EMPTY_SMITHSONIAN_HTML)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].value, 0)
        self.assertTrue(records[0].metadata["empty_report"])
        self.assertEqual(records[1].value, 0)

    @patch("app.ingestion.pipelines.smithsonian_volcanoes.fetch_smithsonian_weekly_report_for_weekstart")
    @patch("app.ingestion.pipelines.smithsonian_volcanoes.httpx.get")
    def test_fetch_smithsonian_weekly_history_aggregates_unique_weeks(self, mock_get, mock_fetch_week):
        class MockResponse:
            text = """
            <html><body><h2>Weekly Volcanic Activity Report for the week of 27 March - 2 April 2026</h2></body></html>
            """

            def raise_for_status(self):
                return None

        mock_get.return_value = MockResponse()
        mock_fetch_week.side_effect = [
            PipelineFetchResult(
                source="smithsonian_volcanoes",
                summary="week one",
                payload={},
                records=[
                    NormalizedObservation(
                        source="smithsonian_volcanoes",
                        metric="weekly_eruption_count",
                        timestamp="2026-04-02T00:00:00+00:00",
                        value=8,
                        metadata={"label": "Weekly eruption count", "unit": "volcanoes"},
                    ),
                    NormalizedObservation(
                        source="smithsonian_volcanoes",
                        metric="active_volcano_count",
                        timestamp="2026-04-02T00:00:00+00:00",
                        value=7,
                        metadata={"label": "Active volcano count", "unit": "volcanoes"},
                    ),
                ],
            ),
            PipelineFetchResult(
                source="smithsonian_volcanoes",
                summary="week two",
                payload={},
                records=[
                    NormalizedObservation(
                        source="smithsonian_volcanoes",
                        metric="weekly_eruption_count",
                        timestamp="2026-03-26T00:00:00+00:00",
                        value=6,
                        metadata={"label": "Weekly eruption count", "unit": "volcanoes"},
                    ),
                    NormalizedObservation(
                        source="smithsonian_volcanoes",
                        metric="active_volcano_count",
                        timestamp="2026-03-26T00:00:00+00:00",
                        value=5,
                        metadata={"label": "Active volcano count", "unit": "volcanoes"},
                    ),
                ],
            ),
            PipelineFetchResult(
                source="smithsonian_volcanoes",
                summary="duplicate week",
                payload={},
                records=[
                    NormalizedObservation(
                        source="smithsonian_volcanoes",
                        metric="weekly_eruption_count",
                        timestamp="2026-04-02T00:00:00+00:00",
                        value=8,
                        metadata={"label": "Weekly eruption count", "unit": "volcanoes"},
                    ),
                    NormalizedObservation(
                        source="smithsonian_volcanoes",
                        metric="active_volcano_count",
                        timestamp="2026-04-02T00:00:00+00:00",
                        value=7,
                        metadata={"label": "Active volcano count", "unit": "volcanoes"},
                    ),
                ],
            ),
        ]

        result = fetch_smithsonian_weekly_history(weeks=3)
        self.assertEqual(result.source, "smithsonian_volcanoes")
        self.assertEqual(len(result.records), 4)
        self.assertEqual(result.payload["weeks_requested"], 3)
        self.assertEqual(result.payload["weeks_backfilled"], 2)
        self.assertEqual(len(result.payload["visited_weekstarts"]), 3)


if __name__ == "__main__":
    unittest.main()
