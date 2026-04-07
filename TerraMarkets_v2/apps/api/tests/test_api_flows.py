from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import db as core_db
from app.main import app
from app.models import auth, data, market, market_data_link, market_snapshot, order, position, purchase_request, user, wallet
from app.models.enums import UserTier
from app.services.auth_service import register_user


class ApiFlowTests(unittest.TestCase):
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

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_register_creates_wallet_with_signup_bonus(self):
        register_response = self.client.post("/auth/register", json={"email": "bonus@example.com", "password": "secret123"})
        self.assertEqual(register_response.status_code, 200)

        login_response = self.client.post("/auth/login", json={"email": "bonus@example.com", "password": "secret123"})
        token = login_response.json()["access_token"]
        wallet_response = self.client.get("/wallet/detail", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(wallet_response.status_code, 200)
        self.assertEqual(wallet_response.json()["balance"], 1000.0)

    def test_buy_rejects_insufficient_balance(self):
        register_response = self.client.post("/auth/register", json={"email": "user2@example.com", "password": "secret123"})
        self.assertEqual(register_response.status_code, 200)
        user_login = self.client.post("/auth/login", json={"email": "user2@example.com", "password": "secret123"})
        user_token = user_login.json()["access_token"]

        admin_login = self.client.post("/auth/login", json={"email": "admin@terramarkets.dev", "password": "adminpass"})
        admin_token = admin_login.json()["access_token"]
        create_market = self.client.post(
            "/markets",
            json={
                "slug": "expensive-market",
                "title": "Expensive market",
                "category": "climate indicators",
                "description": "Market for insufficient balance test",
                "resolution_criteria": "Resolve YES if test condition is met.",
                "close_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "outcomes": ["YES", "NO"],
                "b": 5,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(create_market.status_code, 200)

        buy_response = self.client.post(
            "/markets/expensive-market/buy",
            json={"outcome": "YES", "shares": 1500},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self.assertEqual(buy_response.status_code, 400)
        self.assertIn("Insufficient balance", buy_response.json()["detail"])

    def test_register_login_create_buy_resolve_flow(self):
        register_response = self.client.post("/auth/register", json={"email": "user1@example.com", "password": "secret123"})
        self.assertEqual(register_response.status_code, 200)
        self.assertEqual(register_response.json()["tier"], "free")

        login_response = self.client.post("/auth/login", json={"email": "user1@example.com", "password": "secret123"})
        self.assertEqual(login_response.status_code, 200)
        user_token = login_response.json()["access_token"]

        wallet_response = self.client.get("/wallet", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(wallet_response.status_code, 200)
        self.assertEqual(wallet_response.json()["balance"], 1000.0)

        purchase_request_response = self.client.post(
            "/wallet/purchase-requests",
            json={"amount": 250, "note": "Local test purchase"},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self.assertEqual(purchase_request_response.status_code, 200)
        self.assertEqual(purchase_request_response.json()["status"], "pending")

        admin_login = self.client.post("/auth/login", json={"email": "admin@terramarkets.dev", "password": "adminpass"})
        self.assertEqual(admin_login.status_code, 200)
        admin_token = admin_login.json()["access_token"]

        approve_request = self.client.post(
            f"/wallet/purchase-requests/{purchase_request_response.json()['id']}/approve",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(approve_request.status_code, 200)
        self.assertEqual(approve_request.json()["status"], "approved")

        create_market = self.client.post(
            "/markets",
            json={
                "slug": "test-market",
                "title": "Test market",
                "category": "climate indicators",
                "description": "Integration test market",
                "resolution_criteria": "Resolve YES if the test condition is met.",
                "close_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
                "outcomes": ["YES", "NO"],
                "b": 50,
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(create_market.status_code, 200)
        self.assertEqual(create_market.json()["slug"], "test-market")

        buy_response = self.client.post(
            "/markets/test-market/buy",
            json={"outcome": "YES", "shares": 10},
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self.assertEqual(buy_response.status_code, 200)
        self.assertGreater(buy_response.json()["cost"], 0)

        portfolio_response = self.client.get("/portfolio", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(portfolio_response.status_code, 200)
        portfolio_json = portfolio_response.json()
        self.assertLess(portfolio_json["wallet_balance"], 1250.0)
        self.assertEqual(len(portfolio_json["open_positions"]), 1)
        self.assertEqual(len(portfolio_json["settled_positions"]), 0)
        self.assertEqual(len(portfolio_json["orders"]), 1)
        self.assertGreaterEqual(portfolio_json["total_cost_basis"], 0)

        wallet_detail = self.client.get("/wallet/detail", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(wallet_detail.status_code, 200)
        self.assertGreaterEqual(len(wallet_detail.json()["entries"]), 2)

        admin_users = self.client.get("/wallet/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(admin_users.status_code, 200)
        self.assertGreaterEqual(len(admin_users.json()), 2)

        resolve_response = self.client.post(
            "/markets/test-market/resolve",
            json={"outcome": "YES"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(resolve_response.status_code, 200)
        self.assertEqual(resolve_response.json()["total_paid"], 10.0)

        portfolio_after = self.client.get("/portfolio", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(portfolio_after.status_code, 200)
        self.assertEqual(len(portfolio_after.json()["open_positions"]), 0)
        self.assertEqual(len(portfolio_after.json()["settled_positions"]), 1)
        self.assertEqual(portfolio_after.json()["settled_positions"][0]["resolved_outcome"], "YES")
        self.assertEqual(portfolio_after.json()["settled_positions"][0]["settlement_value"], 10.0)

        wallet_after = self.client.get("/wallet/detail", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(wallet_after.status_code, 200)
        self.assertTrue(any(entry["memo"].startswith("Settlement win") for entry in wallet_after.json()["entries"]))

    def test_non_admin_can_request_data_refresh_but_only_admin_can_list_requests(self):
        register_response = self.client.post("/auth/register", json={"email": "requester@example.com", "password": "secret123"})
        self.assertEqual(register_response.status_code, 200)

        user_login = self.client.post("/auth/login", json={"email": "requester@example.com", "password": "secret123"})
        user_token = user_login.json()["access_token"]

        create_request = self.client.post(
            "/data/fetch-requests",
            json={
                "source_key": "nsidc_charctic_daily",
                "label": "NSIDC Arctic sea ice extent refresh",
                "note": "Please sync the Arctic series",
            },
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self.assertEqual(create_request.status_code, 200)
        self.assertEqual(create_request.json()["status"], "pending")
        self.assertEqual(create_request.json()["requested_by_email"], "requester@example.com")

        user_list_attempt = self.client.get("/data/fetch-requests", headers={"Authorization": f"Bearer {user_token}"})
        self.assertEqual(user_list_attempt.status_code, 403)

        admin_login = self.client.post("/auth/login", json={"email": "admin@terramarkets.dev", "password": "adminpass"})
        admin_token = admin_login.json()["access_token"]
        admin_list = self.client.get("/data/fetch-requests", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(admin_list.status_code, 200)
        self.assertEqual(admin_list.json()[0]["source_key"], "nsidc_charctic_daily")


if __name__ == "__main__":
    unittest.main()
