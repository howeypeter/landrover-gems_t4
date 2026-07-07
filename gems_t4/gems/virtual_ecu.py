"""The virtual GEMS ECU — a state machine that speaks the stylized KWP dialect.

It answers the SID map from INTERFACES.md ($10 session, $3E tester-present,
$21 read-data-by-local-id, $18 read DTCs, $14 clear, $27 security, $30 actuator,
$3B write coding, $1A read id), driving live values from an internal state dict
that a :class:`~gems_t4.gems.scenarios.Scenario` perturbs coherently. It holds a
simple warm-up curve and idle hunt advanced by :meth:`tick`.

No I/O, no real sleep: this is pure logic, so the whole stack is testable off-car.
"""
from __future__ import annotations

import math
from typing import Any

from gems_t4.gems import actuators as _act
from gems_t4.gems import dtc as _dtc
from gems_t4.gems import livedata as _live
from gems_t4.gems.ecu_profile import GEMS_PROFILE, EcuProfile
from gems_t4.gems.immobiliser import (
    ROUTINE_ENTER_LEARN,
    ROUTINE_STATUS,
    ROUTINE_SUBMIT_CODE,
)
from gems_t4.gems.scenarios import HealthyScenario, Scenario
from gems_t4.protocol.messages import NRC, Request, Response
from gems_t4.protocol.security import compute_key

#: Default coding-block contents (local id -> bytes), read/written via 0x21/0x3B.
_DEFAULT_CODING: dict[int, bytes] = {
    0x81: b"123456",      # VIN last 6
    0x82: b"\x00\x01",    # dealer id
    0x83: b"\x46",        # engine: 4.6
    0x84: b"\x01",        # transmission: auto
    0x85: b"\x98\x30",    # build code
    0x86: b"\x01",        # market: NAS (read-only in the tool)
    0x87: b"ERR7109",     # part number (read-only)
}

#: The fixed seed the ECU hands out on SecurityAccess requestSeed (0x27 01).
_SECURITY_SEED = 0x1234


class VirtualEcu:
    """An in-memory GEMS engine ECU. Implements the EcuHandler protocol."""

    def __init__(
        self,
        scenario: Scenario | None = None,
        profile: EcuProfile = GEMS_PROFILE,
        *,
        immobilised: bool = False,
    ) -> None:
        self.profile = profile
        self._scenario: Scenario = scenario or HealthyScenario()
        self._clock = 0.0
        self._unlocked = False
        self._expected_key: int | None = None
        self._coding: dict[int, bytes] = dict(_DEFAULT_CODING)
        # Immobiliser state (the BeCM<->ECM mobilisation). ``immobilised=True``
        # starts desynced — the canon "ENGINE IMMOBILISED" non-start that a
        # Security-Learn re-sync ($31 routines) recovers.
        self._mobilised = not immobilised
        self._learn_mode = False
        self._immo_code = 0xA5A5
        # Baseline live state from the nominal values of every $61 parameter,
        # plus flags scenarios use that are not themselves measures.
        self.state: dict[str, Any] = {
            p.state_key: p.nominal for p in _live.PARAMETERS.values()
        }
        self.state.update(
            engine_running=True,
            o2_heater_ok=True,
            misfire_counts=[0] * 8,
        )
        self._sync_immo_state()
        # DTCs are seeded from the active scenario and cleared by 0x14.
        self._dtcs = list(self._scenario.stored_dtcs())
        # Apply the fault's live-data signature once up front.
        self._scenario.perturb(self.state)

    # -- simulation --------------------------------------------------------- #
    def tick(self, dt: float) -> None:
        """Advance warm-up and idle hunt, then re-assert the fault signature."""
        self._clock += dt
        if self.state.get("engine_running"):
            ct = float(self._coerce(self.state.get("coolant_temp", 85)))
            if ct < 88.0:
                self.state["coolant_temp"] = min(88.0, ct + 4.0 * dt)
            base = float(self._coerce(self.state.get("idle_target", 750)))
            self.state["rpm"] = base + 15.0 * math.sin(self._clock)
        # Fault overrides always win over the nominal simulation.
        self._scenario.perturb(self.state)

    # -- request dispatch --------------------------------------------------- #
    def handle(self, request: Request) -> Response:
        """Route one request to its handler and return the response."""
        handler = {
            0x10: self._session,
            0x3E: self._tester_present,
            0x21: self._read_local_id,
            0x18: self._read_dtcs,
            0x14: self._clear_dtcs,
            0x27: self._security,
            0x30: self._actuator,
            0x31: self._start_routine,
            0x3B: self._write_coding,
            0x1A: self._read_identification,
        }.get(request.service)
        if handler is None:
            return Response.negative(request.service, NRC.SERVICE_NOT_SUPPORTED)
        return handler(request)

    # -- individual services ----------------------------------------------- #
    def _session(self, req: Request) -> Response:
        session = req.data[0] if req.data else 0x81
        return Response.positive(0x10, bytes([session]))

    def _tester_present(self, req: Request) -> Response:
        return Response.positive(0x3E, b"")

    def _read_local_id(self, req: Request) -> Response:
        if not req.data:
            return Response.negative(0x21, NRC.REQUEST_OUT_OF_RANGE)
        local_id = req.data[0]
        param = _live.PARAMETERS.get(local_id)
        if param is not None:
            value = self._coerce(self.state.get(param.state_key, param.nominal))
            return Response.positive(0x21, bytes([local_id]) + param.encode(value))
        if local_id in self._coding:
            return Response.positive(0x21, bytes([local_id]) + self._coding[local_id])
        return Response.negative(0x21, NRC.REQUEST_OUT_OF_RANGE)

    def _read_dtcs(self, req: Request) -> Response:
        return Response.positive(0x18, _dtc.encode_dtc_response(self._dtcs))

    def _clear_dtcs(self, req: Request) -> Response:
        self._dtcs = []
        return Response.positive(0x14, b"")

    def _security(self, req: Request) -> Response:
        if not req.data:
            return Response.negative(0x27, NRC.SUBFUNCTION_NOT_SUPPORTED)
        sub = req.data[0]
        if sub == 0x01:  # requestSeed
            self._expected_key = compute_key(_SECURITY_SEED)
            return Response.positive(
                0x27, bytes([0x01, (_SECURITY_SEED >> 8) & 0xFF, _SECURITY_SEED & 0xFF])
            )
        if sub == 0x02:  # sendKey
            if len(req.data) < 3 or self._expected_key is None:
                return Response.negative(0x27, NRC.REQUEST_SEQUENCE_ERROR)
            key = (req.data[1] << 8) | req.data[2]
            if key == self._expected_key:
                self._unlocked = True
                return Response.positive(0x27, bytes([0x02]))
            return Response.negative(0x27, NRC.INVALID_KEY)
        return Response.negative(0x27, NRC.SUBFUNCTION_NOT_SUPPORTED)

    def _actuator(self, req: Request) -> Response:
        if len(req.data) < 2:
            return Response.negative(0x30, NRC.REQUEST_OUT_OF_RANGE)
        actuator_id, state = req.data[0], req.data[1]
        act = _act.ACTUATORS.get(actuator_id)
        if act is None:
            return Response.negative(0x30, NRC.REQUEST_OUT_OF_RANGE)
        # Interlock: some actuators cannot be driven with the engine running.
        if self.state.get("engine_running") and not act.allowed_engine_running:
            return Response.negative(0x30, NRC.CONDITIONS_NOT_CORRECT)
        # A fault can make a test impossible (e.g. open O2-heater circuit).
        if self._scenario.blocks_actuator(actuator_id):
            return Response.negative(0x30, NRC.CONDITIONS_NOT_CORRECT)
        return Response.positive(0x30, bytes([actuator_id, state]))

    def _start_routine(self, req: Request) -> Response:
        """StartRoutine (0x31) — the Security-Learn immobiliser re-sync routines."""
        if not req.data:
            return Response.negative(0x31, NRC.REQUEST_OUT_OF_RANGE)
        routine = req.data[0]
        if routine == ROUTINE_ENTER_LEARN:
            # Authentic: security access must be granted before a learn.
            if not self._unlocked:
                return Response.negative(0x31, NRC.SECURITY_ACCESS_DENIED)
            self._learn_mode = True
            self._sync_immo_state()
            return Response.positive(0x31, bytes([ROUTINE_ENTER_LEARN]))
        if routine == ROUTINE_SUBMIT_CODE:
            if not self._learn_mode:
                return Response.negative(0x31, NRC.REQUEST_SEQUENCE_ERROR)
            if len(req.data) < 3:
                return Response.negative(0x31, NRC.REQUEST_OUT_OF_RANGE)
            # In learn mode the next code is stored as the new master (not compared).
            self._immo_code = (req.data[1] << 8) | req.data[2]
            self._mobilised = True
            self._learn_mode = False
            self._sync_immo_state()
            return Response.positive(0x31, bytes([ROUTINE_SUBMIT_CODE]))
        if routine == ROUTINE_STATUS:
            return Response.positive(
                0x31,
                bytes([ROUTINE_STATUS, int(self._mobilised), int(self._learn_mode)]),
            )
        return Response.negative(0x31, NRC.REQUEST_OUT_OF_RANGE)

    def _write_coding(self, req: Request) -> Response:
        if not req.data:
            return Response.negative(0x3B, NRC.REQUEST_OUT_OF_RANGE)
        local_id = req.data[0]
        self._coding[local_id] = bytes(req.data[1:])
        return Response.positive(0x3B, bytes([local_id]))

    def _read_identification(self, req: Request) -> Response:
        option = req.data[0] if req.data else 0x00
        return Response.positive(0x1A, bytes([option]) + b"GEMS-EMU-P38")

    # -- helpers ------------------------------------------------------------ #
    def _sync_immo_state(self) -> None:
        """Mirror the immobiliser state into the live-data params that report it
        (``mobilised`` / ``security_learn``), so a $61 read stays consistent."""
        self.state["mobilised"] = 1 if self._mobilised else 0
        self.state["security_learn"] = 0 if self._learn_mode else 1

    @staticmethod
    def _coerce(value: Any) -> float:
        """Coerce a heterogeneous state value into a number for encoding."""
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return value
        if isinstance(value, str):
            return _live.LOOP_MAP.get(value, 0)
        if isinstance(value, (list, tuple)):
            return sum(value)
        return 0
