from __future__ import annotations

import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core import db as core_db
from app.main import app
from app.models import auth, bot, data, market, market_data_link, market_snapshot, order, position, purchase_request, user, wallet
from app.models.bot import BotRun
from app.models.enums import UserTier
from app.services.auth_service import register_user


class DemoMarketTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
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

        db = self.testing_session_local()
        admin = register_user(db, "admin@terramarkets.dev", "adminpass")
        admin.tier = UserTier.admin
        db.commit()
        db.close()

        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        core_db.Base.metadata.drop_all(bind=self.engine)
        core_db.SessionLocal = self.original_session_local
        core_db.engine = self.original_engine
        self.temp_dir.cleanup()

    def login(self, email: str, password: str) -> str:
        response = self.client.post("/auth/login", json={"email": email, "password": password})
        self.assertEqual(response.status_code, 200)
        return response.json()["access_token"]

    def test_admin_can_seed_demo_market_catalog_and_rerun_idempotently(self):
        admin_token = self.login("admin@terramarkets.dev", "adminpass")

        first_seed = self.client.post("/markets/seed/demo", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(first_seed.status_code, 200)
        first_payload = first_seed.json()
        self.assertEqual(len(first_payload["pipelines"]), 6)
        self.assertEqual(first_payload["created_markets"], 18)
        self.assertEqual(first_payload["created_links"], 18)

        second_seed = self.client.post("/markets/seed/demo", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(second_seed.status_code, 200)
        second_payload = second_seed.json()
        self.assertEqual(second_payload["created_markets"], 0)
        self.assertEqual(second_payload["created_links"], 0)
        self.assertEqual(second_payload["existing_markets"], 18)
        self.assertEqual(second_payload["existing_links"], 18)

        markets_response = self.client.get("/markets")
        self.assertEqual(markets_response.status_code, 200)
        self.assertEqual(len(markets_response.json()), 18)

    def test_non_admin_cannot_seed_demo_markets(self):
        register_response = self.client.post("/auth/register", json={"email": "member@example.com", "password": "secret123"})
        self.assertEqual(register_response.status_code, 200)
        user_token = self.login("member@example.com", "secret123")

        response = self.client.post("/markets/seed/demo", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(response.status_code, 403)

    def test_seeded_markets_have_expected_links_and_support_bot_cycle(self):
        admin_token = self.login("admin@terramarkets.dev", "adminpass")
        seed_response = self.client.post("/markets/seed/demo", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(seed_response.status_code, 200)

        expected_links = {
            "arctic-sea-ice-minimum-2026": ("nsidc_charctic_daily", "daily_extent_million_sq_km"),
            "antarctic-sea-ice-maximum-above-18m": ("nsidc_antarctic_daily", "daily_extent_million_sq_km"),
            "enso-oni-above-1-next-release": ("enso_oni", "oni_index"),
            "earthquake-m7-this-month": ("usgs_earthquakes", "earthquake_magnitude"),
            "volcano-weekly-eruptions-above-10": ("smithsonian_volcanoes", "weekly_eruption_count"),
            "solar-flare-m-class-next-30d": ("nasa_donki_solar_flares", "solar_flare_intensity"),
        }
        for slug, (source_key, series_key) in expected_links.items():
            detail = self.client.get(f"/markets/{slug}")
            self.assertEqual(detail.status_code, 200)
            links = detail.json()["data_links"]
            self.assertTrue(any(link["source_key"] == source_key and link["series_key"] == series_key for link in links))

        bot_seed_response = self.client.post("/bots/seed/defaults", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(bot_seed_response.status_code, 200)

        cycle_response = self.client.post(
            "/bots/run-cycle",
            json={"trigger_source": "manual", "market_slug": "enso-oni-above-1-next-release"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(cycle_response.status_code, 200)
        runs = cycle_response.json()
        self.assertGreaterEqual(len(runs), 9)

        db = self.testing_session_local()
        try:
            self.assertGreaterEqual(len(db.scalars(select(BotRun)).all()), 9)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
