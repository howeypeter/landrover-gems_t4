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


def test_live_measures_have_unique_ids(client: TestClient) -> None:
    # Regression: `raw` (the undecoded value) was exposed as the id, so ~16
    # measures collided on pid 0x00 and the web UI rendered duplicate gauges.
    # Every measure must carry a distinct local id / PID and a distinct name.
    ms = client.get("/api/live").json()["measures"]
    pids = [m["pid"] for m in ms]
    names = [m["name"] for m in ms]
    assert None not in pids, "every virtual measure has a local id"
    assert len(set(pids)) == len(pids), "measure ids must be unique (no collisions)"
    assert len(set(names)) == len(names), "measure names must be unique"


def test_live_pid_filter(client: TestClient) -> None:
    # A single-id request narrows the set vs. the full read (fast single-sensor
    # path). On the virtual ECU the filter is by local id; on the real ECU by
    # OBD PID - here we just prove the filter is applied, not the id semantics.
    full = client.get("/api/live").json()["measures"]
    one = client.get("/api/live", params={"pid": "00"}).json()["measures"]
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
    with client.websocket_connect("/api/live/stream?pid=00&hz=8") as ws:
        msg = ws.receive_json()
        assert "measures" in msg and msg["measures"]


def test_immobiliser_status(client: TestClient) -> None:
    body = client.get("/api/immobiliser").json()
    assert set(body) == {"mobilised", "learn_mode"}


def test_actuator_run(client: TestClient) -> None:
    a = client.get("/api/actuators").json()["actuators"][0]
    r = client.post("/api/actuator", json={"actuator_id": a["id"], "state": 1})
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"actuator_id", "ok", "message"}
    assert isinstance(body["ok"], bool)


def test_coding_read_and_write(client: TestClient) -> None:
    fields = client.get("/api/coding").json()["fields"]
    assert fields
    assert {"key", "name", "writable", "value"} <= set(fields[0])
    writable = next((f for f in fields if f["writable"]), None)
    if writable is not None:
        # Round-trip a write through the gated Backend path (API confirms server
        # side). Use the current value so the round-trip is a no-op on the ECU.
        text = writable["value"] or "000000"
        r = client.post("/api/coding", json={"field": writable["key"], "text": text})
        assert r.status_code == 200
        assert r.json()["field"] == writable["key"]


def test_vin_endpoint(client: TestClient) -> None:
    r = client.get("/api/vin")
    assert r.status_code == 200
    assert "vin" in r.json()          # value may be a string or null


def test_maps_endpoint(client: TestClient) -> None:
    r = client.get("/api/maps")
    assert r.status_code == 200
    assert isinstance(r.json()["maps"], list)


def test_connection_test_endpoint(client: TestClient) -> None:
    r = client.post("/api/connection/test")
    assert r.status_code == 200
    body = r.json()
    assert {"ok", "label", "message", "latencies_ms"} <= set(body)
