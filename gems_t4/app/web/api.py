"""FastAPI application over the Backend.

Every endpoint is a thin wrapper around a single shared
:class:`gems_t4.app.backend.Backend`. Because the transport is single-connection
(one tester per K-line at a time) and ``Backend`` is not thread-safe, ALL backend
access is serialized behind one lock - FastAPI runs sync ``def`` endpoints in a
threadpool, so the lock is what keeps concurrent HTTP requests from colliding on
the ECU.

Serialization is deliberately plain dicts (no ORM) so the JSON shape is obvious
to the front-end. Write endpoints (actuator/coding/immobiliser) go through the
same gated Backend methods the CLI/GUI use - the API adds no new authority.
"""
from __future__ import annotations

import threading
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from gems_t4.app.backend import Backend
from gems_t4.transport.base import TransportError

# ---- serialization helpers (dataclasses/namedtuples -> plain dicts) --------- #


def _measure(m: Any) -> dict:
    pid = m.raw if isinstance(m.raw, int) else None
    return {"name": m.name, "value": m.value, "unit": m.unit,
            "pid": pid, "pid_hex": (f"0x{pid:02X}" if pid is not None else None)}


def _dtc(d: Any) -> dict:
    state = getattr(d.state, "value", d.state)
    return {"code": d.code, "description": d.description, "raw": d.raw, "state": state}


def _actuator(a: Any) -> dict:
    return {"id": a.actuator_id, "name": a.name,
            "allowed_engine_running": a.allowed_engine_running}


# ---- request bodies --------------------------------------------------------- #


class ConnectionBody(BaseModel):
    kind: str = "virtual"                 # virtual | usb | ble | network
    com_port: str | None = None
    host: str | None = None
    tcp_port: int = 9141
    device: str | None = None
    allow_writes: bool = False
    real_ecu: bool | None = None          # kline commands force the real profile


class ScenarioBody(BaseModel):
    scenario: str


class ActuatorBody(BaseModel):
    actuator_id: int
    state: int


class CodingBody(BaseModel):
    field: str
    text: str


# ---- app factory ------------------------------------------------------------ #


def build_app(backend: Backend | None = None) -> FastAPI:
    """Create the FastAPI app around one Backend (a fresh virtual one by default).

    Pass an existing ``backend`` in tests to control scenario/connection.
    """
    app = FastAPI(title="gems_t4 API", version="0.1.0")
    app.state.backend = backend or Backend()
    app.state.lock = threading.Lock()

    def be() -> Backend:
        return app.state.backend

    def locked(fn, *a, **k):
        """Run a Backend call under the shared lock (sync helper)."""
        with app.state.lock:
            return fn(*a, **k)

    # -- status / connection -------------------------------------------------- #
    @app.get("/api/status")
    def status() -> dict:
        b = be()
        return {
            "connected": b.connected,
            "connection_label": b.connection_label,
            "connection_kind": b.connection_kind,
            "on_real_ecu": b.on_real_ecu,
            "is_remote": b.is_remote,
            "scenario": b.scenario_name,
            "adapter_firmware": locked(b.adapter_firmware) if b.connected else None,
        }

    @app.get("/api/scenarios")
    def scenarios() -> dict:
        return {"scenarios": be().available_scenarios(),
                "current": be().scenario_name}

    @app.post("/api/scenario")
    def set_scenario(body: ScenarioBody) -> dict:
        try:
            be().set_scenario(body.scenario)
        except (ValueError, KeyError) as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"scenario": be().scenario_name}

    @app.post("/api/connection")
    def apply_connection(body: ConnectionBody) -> dict:
        b = be()
        try:
            label = locked(
                b.apply_connection, body.kind, com_port=body.com_port,
                host=body.host, tcp_port=body.tcp_port, device=body.device,
                allow_writes=body.allow_writes, real_ecu=body.real_ecu,
            )
        except (TransportError, OSError, ValueError) as exc:
            # Connection failed and Backend rolled back. Report why, incl. the
            # adapter firmware if the Pico link was up but the ECU stayed silent.
            fw = b.last_adapter_firmware
            detail = str(exc)
            if fw:
                detail = f"Pico connected (fw {fw}) but the ECU did not answer: {detail}"
            raise HTTPException(502, detail) from exc
        return {"connected": b.connected, "connection_label": label,
                "connection_kind": b.connection_kind,
                "adapter_firmware": b.last_adapter_firmware}

    @app.post("/api/connection/test")
    def test_connection() -> dict:
        r = locked(be().test_connection)
        return {"ok": r.ok, "label": r.label, "message": r.message,
                "latencies_ms": list(r.latencies_ms)}

    @app.post("/api/disconnect")
    def disconnect() -> dict:
        locked(be().disconnect)
        return {"connected": be().connected}

    # -- live data ------------------------------------------------------------ #
    def _read_live(pids: list[int] | None) -> list[dict]:
        return [_measure(m) for m in locked(be().read_live, pids)]

    @app.get("/api/live")
    def live(pid: list[str] | None = Query(default=None)) -> dict:
        pids = _parse_pids(pid)
        try:
            return {"measures": _read_live(pids)}
        except Exception as exc:  # noqa: BLE001 - surface as 409 (not connected etc.)
            raise HTTPException(409, str(exc)) from exc

    @app.websocket("/api/live/stream")
    async def live_stream(ws: WebSocket) -> None:
        await ws.accept()
        pids = _parse_pids(ws.query_params.getlist("pid"))
        try:
            hz = float(ws.query_params.get("hz", "4"))
        except (TypeError, ValueError):
            hz = 4.0
        interval = 1.0 / max(0.5, min(20.0, hz))
        try:
            while True:
                try:
                    measures = await run_in_threadpool(_read_live, pids)
                    await run_in_threadpool(lambda: locked(be().tick, interval))
                except Exception as exc:  # noqa: BLE001
                    await ws.send_json({"error": str(exc)})
                    break
                await ws.send_json({"measures": measures})
                await _sleep(interval)
        except WebSocketDisconnect:
            return

    # -- fault codes ---------------------------------------------------------- #
    @app.get("/api/dtcs")
    def dtcs() -> dict:
        try:
            return {"dtcs": [_dtc(d) for d in locked(be().read_dtcs)]}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(409, str(exc)) from exc

    @app.post("/api/dtcs/clear")
    def clear_dtcs() -> dict:
        try:
            return {"cleared": bool(locked(be().clear_dtcs))}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(409, str(exc)) from exc

    # -- actuators ------------------------------------------------------------ #
    @app.get("/api/actuators")
    def actuators() -> dict:
        return {"actuators": [_actuator(a) for a in be().actuator_list()]}

    @app.post("/api/actuator")
    def run_actuator(body: ActuatorBody) -> dict:
        try:
            r = locked(be().run_actuator, body.actuator_id, body.state)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(409, str(exc)) from exc
        return {"actuator_id": r.actuator_id, "ok": r.ok, "message": r.message}

    # -- identity / coding / immobiliser -------------------------------------- #
    @app.get("/api/vin")
    def vin() -> dict:
        try:
            return {"vin": locked(be().read_vin)}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/coding")
    def coding() -> dict:
        fields = []
        for f in be().coding_fields():
            item = {"key": f.key, "name": f.name, "writable": f.writable}
            try:
                item["value"] = locked(be().read_coding_text, f.key)
            except Exception:  # noqa: BLE001 - value unavailable is not fatal
                item["value"] = None
            fields.append(item)
        return {"fields": fields}

    @app.post("/api/coding")
    def write_coding(body: CodingBody) -> dict:
        try:
            data = be().encode_coding_text(body.field, body.text)

            # Full gated write: read-before-write backup, then write with
            # verify-after-write. The browser already confirmed (see the UI),
            # so confirm() is satisfied here.
            def _do() -> None:
                bk = be().backup_coding(body.field)
                be().write_coding(body.field, data, backup=bk, confirm=lambda: True)

            locked(_do)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(409, str(exc)) from exc
        return {"field": body.field, "value": locked(be().read_coding_text, body.field)}

    @app.get("/api/immobiliser")
    def immobiliser() -> dict:
        try:
            s = locked(be().immobiliser_status)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(409, str(exc)) from exc
        return {"mobilised": s.mobilised, "learn_mode": s.learn_mode}

    # -- maps ----------------------------------------------------------------- #
    @app.get("/api/maps")
    def maps() -> dict:
        return {"maps": be().available_maps()}

    # -- static front-end (built React app, if present) ----------------------- #
    # `frontend/npm run build` outputs here; served at / so `gems_t4 api` hosts
    # the UI too. Absent in a source checkout -> the API still runs headless.
    import pathlib

    static_dir = pathlib.Path(__file__).with_name("static")
    if static_dir.is_dir():
        from fastapi.staticfiles import StaticFiles
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="ui")

    return app


# ---- module helpers --------------------------------------------------------- #


def _parse_pids(pid: list[str] | None) -> list[int] | None:
    if not pid:
        return None
    out: list[int] = []
    for p in pid:
        try:
            out.append(int(p, 16))
        except (TypeError, ValueError):
            continue
    return out or None


async def _sleep(seconds: float) -> None:
    import asyncio
    await asyncio.sleep(seconds)
