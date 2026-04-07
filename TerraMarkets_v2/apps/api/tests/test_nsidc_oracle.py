from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import db as core_db
from app.models import data, market, market_data_link, market_snapshot, order, position, purchase_request, user, wallet, auth
from app.oracles.nsidc_charctic import parse_nsidc_daily_extent_csv
from app.services.data_service import ingest_data_run


SAMPLE_CSV = """Date generated: 2026-03-16
source: NSIDC demo
Year,Month,Day,Extent,Missing,Source Data
2026,03,13,14.21,0,SMMR
2026,03,14,14.18,0,SMMR
2026,03,15,14.12,0,SMMR
"""


class NsidcOracleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        db_path = f"{self.temp_dir.name}/test.db"
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            future=True,
        )
        self.testing_session_local = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            future=True,
        )
        self.original_engine = core_db.engine
        self.original_session_local = core_db.SessionLocal
        core_db.engine = self.engine
        core_db.SessionLocal = self.testing_session_local
        core_db.Base.metadata.create_all(bind=self.engine)

    def tearDown(self):
        core_db.Base.metadata.drop_all(bind=self.engine)
        core_db.SessionLocal = self.original_session_local
        core_db.engine = self.original_engine
        self.temp_dir.cleanup()

    def test_parse_nsidc_daily_extent_csv(self):
        points = parse_nsidc_daily_extent_csv(SAMPLE_CSV, days=2)
        self.assertEqual(len(points), 2)
        self.assertEqual(points[0]["series_key"], "daily_extent_million_sq_km")
        self.assertEqual(points[0]["numeric_value"], 14.18)
        self.assertEqual(points[1]["numeric_value"], 14.12)
        self.assertEqual(points[1]["unit"], "million sq km")
        self.assertIn("2026-03-15", points[1]["observed_at"])

    def test_ingest_data_run_accepts_iso_datetime_strings(self):
        db = self.testing_session_local()
        try:
            run = ingest_data_run(
                db,
                source_key="nsidc_charctic_daily",
                summary="Test run",
                payload={},
                points=parse_nsidc_daily_extent_csv(SAMPLE_CSV, days=2),
            )
            db.commit()
            self.assertEqual(run.source_key, "nsidc_charctic_daily")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
