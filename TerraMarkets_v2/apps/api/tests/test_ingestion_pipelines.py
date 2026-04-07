from __future__ import annotations

import unittest

from app.ingestion.pipelines.donki_solar_flares import normalize_donki_flares
from app.ingestion.pipelines.enso_oni import parse_oni_html_table
from app.ingestion.pipelines.usgs_earthquakes import parse_usgs_geojson


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


if __name__ == "__main__":
    unittest.main()
