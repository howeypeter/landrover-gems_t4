"""The GUI/CLI backend facade — a Qt-free seam over the gems_core stack.

``Backend`` hides the VirtualEcu → VirtualTransport → KwpClient wiring behind a
handful of high-level methods (connect, read live data, read/clear DTCs, run an
actuator, change scenario). It has NO Qt dependency, so it is fully unit-testable
without a display, and the PySide6 screens talk only to this — never to the
protocol/transport layers directly.

For now it drives the in-memory virtual ECU. A real-hardware path (a Pico
transport) can be dropped in later via ``transport_factory`` without changing any
screen code — the same seam the CLI already uses.
"""
from __future__ import annotations

from typing import Callable

from gems_t4.gems import actuators as _actuators
from gems_t4.gems import dtc as _dtc
from gems_t4.gems import immobiliser as _immo
from gems_t4.gems import livedata as _livedata
from gems_t4.gems import maps as _maps
from gems_t4.gems import programming as _prog
from gems_t4.gems.actuators import ActuatorDef, ActuatorOutcome
from gems_t4.gems.immobiliser import ImmobiliserStatus, SecurityLearnResult
from gems_t4.gems.maps import MapTable
from gems_t4.gems.programming import Backup, CodingField, WriteResult
from gems_t4.gems.scenarios import SCENARIOS, get_scenario
from gems_t4.gems.types import Dtc, Measure
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.protocol.security import compute_key
from gems_t4.transport.base import Transport
from gems_t4.transport.virtual import VirtualTransport


class Backend:
    """High-level diagnostic session for the GUI (and reusable elsewhere).

    Parameters
    ----------
    scenario:
        Name of the initial fault scenario (see :data:`SCENARIOS`).
    transport_factory:
        Optional callable returning a :class:`Transport` to use instead of the
        in-memory virtual ECU (e.g. a Pico adapter). When given, ``scenario`` is
        ignored and there is no local :class:`VirtualEcu` to ``tick``.
    """

    def __init__(
        self,
        scenario: str = "healthy",
        *,
        immobilised: bool = False,
        transport_factory: Callable[[], Transport] | None = None,
    ) -> None:
        self._scenario_name = scenario
        self._immobilised = immobilised
        self._transport_factory = transport_factory
        self._client: KwpClient | None = None
        self._ecu: VirtualEcu | None = None

    # -- introspection ------------------------------------------------------ #
    @property
    def scenario_name(self) -> str:
        return self._scenario_name

    @property
    def connected(self) -> bool:
        return self._client is not None

    @property
    def is_wireless(self) -> bool:
        """False for the wired/virtual paths; a future WiFi transport sets True."""
        t = getattr(self._client, "transport", None)
        return bool(getattr(t, "is_wireless", False))

    @staticmethod
    def available_scenarios() -> list[str]:
        return list(SCENARIOS)

    @staticmethod
    def actuator_list() -> list[ActuatorDef]:
        return list(_actuators.ACTUATORS.values())

    # -- session lifecycle -------------------------------------------------- #
    def set_scenario(self, name: str) -> None:
        """Select a fault scenario. Reconnects if a session is already open."""
        get_scenario(name)  # validate; raises KeyError on unknown
        self._scenario_name = name
        if self.connected:
            self.disconnect()
            self.connect()

    def connect(self) -> None:
        """Open a diagnostic session (build the stack, init, start session)."""
        if self.connected:
            return
        if self._transport_factory is not None:
            transport = self._transport_factory()
            self._ecu = None
        else:
            self._ecu = VirtualEcu(
                get_scenario(self._scenario_name), immobilised=self._immobilised
            )
            transport = VirtualTransport(self._ecu)
        client = KwpClient(transport)
        client.connect()
        client.start_session()
        self._client = client

    def disconnect(self) -> None:
        """Close the session (idempotent)."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:  # pragma: no cover - best-effort
                pass
        self._client = None
        self._ecu = None

    def _require(self) -> KwpClient:
        if self._client is None:
            self.connect()
        assert self._client is not None
        return self._client

    def tick(self, dt: float) -> None:
        """Advance the virtual ECU's simulation (warm-up curve, idle hunt).

        No-op on a real-hardware transport (there is no local ECU to tick).
        """
        if self._ecu is not None:
            self._ecu.tick(dt)

    # -- diagnostic operations --------------------------------------------- #
    def read_live(self, ids: list[int] | None = None) -> list[Measure]:
        """Read live-data measures (all known ids by default)."""
        return _livedata.read_all(self._require(), ids)

    def read_dtcs(self) -> list[Dtc]:
        """Read stored fault codes."""
        return _dtc.read_dtcs(self._require())

    def clear_dtcs(self) -> None:
        """Clear stored fault codes."""
        _dtc.clear_dtcs(self._require())

    def run_actuator(self, actuator_id: int, state: int) -> ActuatorOutcome:
        """Command an actuator test; returns the outcome (incl. refusals)."""
        return _actuators.run(self._require(), actuator_id, state)

    # -- coding / programming (gated writes) ------------------------------- #
    @staticmethod
    def coding_fields() -> list[CodingField]:
        return list(_prog.CODING_FIELDS.values())

    def read_coding(self, field: str) -> bytes:
        """Read a coding field's current bytes."""
        return _prog.read_coding(self._require(), field)

    def read_coding_text(self, field: str) -> str:
        """Read a coding field rendered for display (ASCII or hex)."""
        return _prog.decode_field(field, self.read_coding(field))

    def backup_coding(self, field: str) -> Backup:
        """Take a verified read-before-write backup of a coding field."""
        return _prog.backup(self._require(), field)

    def write_coding(
        self,
        field: str,
        value: bytes,
        *,
        backup: Backup,
        verify: bool = True,
        confirm: Callable[[], bool] | None = None,
    ) -> WriteResult:
        """Write a coding field through every safety gate (see gems/programming)."""
        return _prog.write_coding(
            self._require(), field, value, backup=backup, verify=verify, confirm=confirm
        )

    @staticmethod
    def encode_coding_text(field: str, text: str) -> bytes:
        """Parse an edited coding value string back to bytes."""
        return _prog.encode_field(field, text)

    # -- immobiliser / Security-Learn -------------------------------------- #
    def set_immobilised(self, immobilised: bool) -> None:
        """Force the ENGINE IMMOBILISED failure mode on/off (rebuilds the ECU)."""
        self._immobilised = immobilised
        if self.connected:
            self.disconnect()
            self.connect()

    def immobiliser_status(self) -> ImmobiliserStatus:
        """Read the ECU immobiliser status (mobilised / learn mode)."""
        return _immo.read_status(self._require())

    def security_access(self) -> None:
        """Perform SecurityAccess ($27 seed/key) on the ECU."""
        self._require().security_access(compute_key)

    def security_learn(
        self,
        becm_code: int = _immo.DEFAULT_BECM_CODE,
        *,
        on_progress: Callable[[str], None] | None = None,
    ) -> SecurityLearnResult:
        """Run the full immobiliser Security-Learn re-sync."""
        return _immo.security_learn(self._require(), becm_code, on_progress=on_progress)

    # -- maps (chip-swap lookalike) ---------------------------------------- #
    @staticmethod
    def available_maps() -> list[str]:
        return list(_maps.MAPS)

    @staticmethod
    def get_map(token: str) -> MapTable:
        return _maps.MAPS[token]
