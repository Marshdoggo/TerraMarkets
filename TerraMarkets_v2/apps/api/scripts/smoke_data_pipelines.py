from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def main() -> int:
    client = TestClient(app)
    login = client.post("/auth/login", json={"email": "admin@terramarkets.dev", "password": "adminpass"})
    print("login_status", login.status_code)
    if login.status_code != 200:
        print(login.text)
        return 1

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    endpoints = [
        ("/data/fetch/enso-oni", {"source_key": "enso_oni"}),
        ("/data/fetch/usgs-earthquakes", {"source_key": "usgs_earthquakes"}),
        ("/data/fetch/donki-solar-flares", {"source_key": "nasa_donki_solar_flares"}),
    ]

    for path, body in endpoints:
        try:
            response = client.post(path, json=body, headers=headers)
            print("endpoint", path, "status", response.status_code)
            print(response.text[:800])
        except Exception as exc:
            print("endpoint", path, "error", repr(exc))

    runs = client.get("/data/runs")
    print("runs_status", runs.status_code)
    print(runs.text[:2200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
