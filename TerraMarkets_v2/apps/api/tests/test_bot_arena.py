from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core import db as core_db
from app.main import app
from app.models import auth, bot, data, market, market_data_link, market_snapshot, order, position, purchase_request, user, wallet
from app.models.bot import BotProfile, BotRun
from app.models.data import DataSourceRun
from app.models.enums import UserTier
from app.services.auth_service import register_user
from app.services.bot_service import HedgerStrategy, OpenAIBotStrategy, SpeculatorStrategy, TrendFollowerStrategy


class BotArenaTests(unittest.TestCase):
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

    def create_market(self, admin_token: str, slug: str, category: str = "climate indicators") -> None:
        response = self.client.post(
            "/markets",
            json={
                "slug": slug,
                "title": f"Market {slug}",
                "category": category,
                "description": f"Description for {slug}",
                "resolution_criteria": "Resolve YES if the described condition is met by the close date.",
                "close_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "outcomes": ["YES", "NO"],
                "b": 50,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_strategy_policies_return_expected_actions(self):
        base_bot = SimpleNamespace(config_json={"momentum_threshold": 0.02, "min_spread": 0.08, "value_threshold": 0.42, "rebalance_threshold": 0.65}, strategy_type="trend_follower")
        trend_context = {
            "bot": base_bot,
            "prices": {"YES": 0.62, "NO": 0.38},
            "snapshots": [SimpleNamespace(prices={"YES": 0.62, "NO": 0.38}), SimpleNamespace(prices={"YES": 0.55, "NO": 0.45})],
            "share_budget": 40,
        }
        trend_decision = TrendFollowerStrategy().decide(trend_context)
        self.assertEqual(trend_decision.action_type, "buy")
        self.assertEqual(trend_decision.outcome, "YES")

        spec_context = {
            "bot": base_bot,
            "prices": {"YES": 0.31, "NO": 0.69},
            "share_budget": 35,
        }
        spec_decision = SpeculatorStrategy().decide(spec_context)
        self.assertEqual(spec_decision.action_type, "buy")
        self.assertEqual(spec_decision.outcome, "YES")

        hedger_context = {
            "bot": base_bot,
            "prices": {"YES": 0.48, "NO": 0.52},
            "exposure_by_outcome": {"YES": 90.0},
            "share_budget": 20,
        }
        hedge_decision = HedgerStrategy().decide(hedger_context)
        self.assertEqual(hedge_decision.action_type, "buy")
        self.assertEqual(hedge_decision.outcome, "NO")

    def test_openai_strategy_holds_when_disabled(self):
        original_enabled = settings.OPENAI_BOT_ENABLED
        settings.OPENAI_BOT_ENABLED = False
        try:
            decision = OpenAIBotStrategy().decide({"bot": SimpleNamespace(strategy_type="openclaw_agent")})
            self.assertEqual(decision.action_type, "hold")
            self.assertIn("disabled", decision.thesis_summary.lower())
        finally:
            settings.OPENAI_BOT_ENABLED = original_enabled

    def test_seed_default_bots_and_run_cycle_creates_runs_and_orders(self):
        admin_token = self.login("admin@terramarkets.dev", "adminpass")
        self.create_market(admin_token, "bot-cycle-market")

        seed_response = self.client.post("/bots/seed/defaults", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(seed_response.status_code, 200)
        self.assertGreaterEqual(seed_response.json()["bot_count"], 3)

        cycle_response = self.client.post(
            "/bots/run-cycle",
            json={"trigger_source": "manual", "market_slug": "bot-cycle-market"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(cycle_response.status_code, 200)
        runs = cycle_response.json()
        self.assertGreaterEqual(len(runs), 3)
        self.assertTrue(any(run["action_type"] == "buy" for run in runs))

        users_response = self.client.get("/wallet/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(users_response.status_code, 200)
        self.assertTrue(any(user["email"].endswith("@bots.terramarkets.dev") for user in users_response.json()))

        db = self.testing_session_local()
        try:
            self.assertGreaterEqual(len(db.scalars(select(BotProfile)).all()), 3)
            self.assertGreaterEqual(len(db.scalars(select(BotRun)).all()), 3)
            self.assertGreaterEqual(len(db.scalars(select(order.Order)).all()), 1)
        finally:
            db.close()

        commentary_response = self.client.get("/markets/bot-cycle-market/bot-commentary")
        self.assertEqual(commentary_response.status_code, 200)
        commentary = commentary_response.json()
        self.assertGreaterEqual(len(commentary), 1)
        self.assertIn("bot_display_name", commentary[0])
        self.assertIn("thesis_summary", commentary[0])
        self.assertNotIn("email", commentary[0])

    def test_non_admin_cannot_access_bot_controls(self):
        register_response = self.client.post("/auth/register", json={"email": "user@example.com", "password": "secret123"})
        self.assertEqual(register_response.status_code, 200)
        user_token = self.login("user@example.com", "secret123")

        response = self.client.get("/bots", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(response.status_code, 403)

    def test_data_ingest_triggers_event_driven_bot_runs(self):
        admin_token = self.login("admin@terramarkets.dev", "adminpass")
        self.create_market(admin_token, "event-driven-market", category="arctic systems")
        link_response = self.client.post(
            "/markets/event-driven-market/links",
            json={
                "source_key": "enso_oni",
                "series_key": "oni_value",
                "label": "ENSO benchmark",
                "notes": "Used to trigger bot reevaluations.",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(link_response.status_code, 200)

        seed_response = self.client.post("/bots/seed/defaults", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(seed_response.status_code, 200)

        ingest_response = self.client.post(
            "/data/ingest",
            json={
                "source_key": "enso_oni",
                "summary": "Synthetic ENSO update",
                "payload": {"mode": "test"},
                "points": [
                    {
                        "series_key": "oni_value",
                        "label": "ENSO ONI",
                        "numeric_value": 1.2,
                        "unit": "index",
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                        "metadata_json": {"source": "test"},
                    }
                ],
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(ingest_response.status_code, 200)

        bots_response = self.client.get("/bots", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(bots_response.status_code, 200)
        recent_runs = [run for bot_payload in bots_response.json() for run in bot_payload["recent_runs"]]
        self.assertTrue(any(run["trigger_source"] == "data_refresh" for run in recent_runs))

    def test_fetch_all_preserves_partial_successes(self):
        admin_token = self.login("admin@terramarkets.dev", "adminpass")

        def make_run(db, source_key):
            run = DataSourceRun(
                source_key=source_key,
                status="success",
                summary=f"Fake {source_key}",
                payload={"points_received": 1, "points_inserted": 1},
            )
            db.add(run)
            db.commit()
            db.refresh(run)
            return run

        def fake_pipeline_fetch(db, *, source_key, admin_id):
            if source_key == "usgs_earthquakes":
                raise RuntimeError("USGS unavailable")
            return make_run(db, source_key)

        with (
            patch("app.api.routers.data._ingest_nsidc_fetch", side_effect=lambda db, admin_id: make_run(db, "nsidc_charctic_daily")),
            patch("app.api.routers.data._ingest_pipeline_fetch", side_effect=fake_pipeline_fetch),
        ):
            response = self.client.post("/data/fetch/all", headers={"Authorization": f"Bearer {admin_token}"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "partial_failure")
        statuses = {result["source_key"]: result["status"] for result in payload["results"]}
        self.assertEqual(statuses["nsidc_charctic_daily"], "success")
        self.assertEqual(statuses["enso_oni"], "success")
        self.assertEqual(statuses["usgs_earthquakes"], "failed")


if __name__ == "__main__":
    unittest.main()
