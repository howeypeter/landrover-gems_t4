"""API layer tests - the FastAPI wrapper over the Backend (virtual ECU).

Skips cleanly if FastAPI/httpx aren't installed (the [api] extra).
"""
from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from gems_t4.app.backend import Backend  # noqa: E402
from gems_t4.app.web import build_app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    # A known scenario so DTCs/live are deterministic.
    return TestClient(build_app(Backend("misfire_cyl3")))


def test_status_reports_virtual(client: TestClient) -> None:
    r = client.get("/api/status")
    assert r.status_code == 200
    body = r.json()
    assert body["scenario"] == "misfire_cyl3"
    assert body["on_real_ecu"] is False
    assert body["adapter_firmware"] is None       # virtual: no adapter


def test_scenarios_and_switch(client: TestClient) -> None:
    r = client.get("/api/scenarios")
    assert "healthy" in r.json()["scenarios"]
    r = client.post("/api/scenario", json={"scenario": "healthy"})
    assert r.status_code == 200 and r.json()["scenario"] == "healthy"
    r = client.post("/api/scenario", json={"scenario": "nope"})
    assert r.status_code == 400


def test_live_returns_measures(client: TestClient) -> None:
    body = client.get("/api/live").json()
    assert body["measures"], "expected live measures"
    m = body["measures"][0]
    assert {"name", "value", "unit", "pid"} <= set(m)


def test_live_pid_filter(client: TestClient) -> None:
    # A single-id request narrows the set vs. the full read (fast single-sensor
    # path). On the virtual ECU the filter is by local id; on the real ECU by
    # OBD PID - here we just prove the filter is applied, not the id semantics.
    full = client.get("/api/live").json()["measures"]
    one = client.get("/api/live", params={"pid": "0C"}).json()["measures"]
    assert 0 < len(one) < len(full)


def test_dtcs_for_scenario(client: TestClient) -> None:
    body = client.get("/api/dtcs").json()
    codes = {d["code"] for d in body["dtcs"]}
    assert any(c.startswith("P") for c in codes)       # misfire scenario has codes


def test_clear_dtcs(client: TestClient) -> None:
    assert client.post("/api/dtcs/clear").json()["cleared"] in (True, False)


def test_actuators_listed(client: TestClient) -> None:
    body = client.get("/api/actuators").json()
    assert body["actuators"]
    assert {"id", "name", "allowed_engine_running"} <= set(body["actuators"][0])


def test_live_stream_websocket(client: TestClient) -> None:
    with client.websocket_connect("/api/live/stream?pid=0C&hz=8") as ws:
        msg = ws.receive_json()
        assert "measures" in msg and msg["measures"]


def test_immobiliser_status(client: TestClient) -> None:
    body = client.get("/api/immobiliser").json()
    assert set(body) == {"mobilised", "learn_mode"}
