"""Fault scenarios for the virtual GEMS ECU.

A :class:`Scenario` bundles three things so that a technician's
read -> diagnose -> clear workflow is internally coherent:

* :meth:`Scenario.stored_dtcs` — the P-codes the ECU will report to a
  ``ReadDTCByStatus`` (0x18) request.
* :meth:`Scenario.perturb` — an in-place mutation of the live-data state dict
  so that the $61 live measures reflect the *same* fault (e.g. a coolant-sensor
  fault makes the coolant reading jump to its fail-safe substitution).
* :meth:`Scenario.blocks_actuator` — whether a given actuator test should be
  refused because of the fault (e.g. an O2-heater open circuit means the O2
  heater actuator test cannot pass).

The four scenarios (``healthy``, ``coolant_sensor``, ``misfire_cyl3``,
``lambda_heater``) map onto the DTC groups and fail-safe substitutions from
``memory/research/gems-data-catalog.md``.

This module is pure data + logic: no I/O, no sleep. The DTC P-codes are looked
up against :mod:`gems_t4.gems.dtc` when it is available, but each scenario also
carries the description text inline so it is self-contained for testing.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from gems_t4.gems.types import Dtc, DtcState

# ---------------------------------------------------------------------------
# Actuator ids (mirrors gems.actuators.ACTUATORS ids from INTERFACES.md).
# Kept as local constants so scenarios do not hard-depend on Agent 2's module
# import-order; the numeric ids are the contract.
# ---------------------------------------------------------------------------
ACT_MIL = 0x01
ACT_O2_HEATER = 0x02
ACT_FUEL_PUMP = 0x03
ACT_AC_GRANT = 0x04
ACT_CONDENSER_FAN = 0x05


@runtime_checkable
class Scenario(Protocol):
    """A coherent fault (or health) profile for the virtual ECU."""

    name: str

    def stored_dtcs(self) -> list[Dtc]:
        """Return the DTCs this scenario stores (empty list = no faults)."""
        ...

    def perturb(self, state: dict) -> None:
        """Mutate the live-data ``state`` dict in place to reflect the fault."""
        ...

    def blocks_actuator(self, actuator_id: int) -> bool:
        """Return True if this fault should make the given actuator test fail."""
        ...


def _dtc(code: str, description: str, raw: int, state: DtcState = DtcState.ACTIVE) -> Dtc:
    """Build a :class:`Dtc`, preferring the canonical description/raw from
    :mod:`gems_t4.gems.dtc` when that module is importable.

    Falls back to the inline text so scenarios remain usable while Agent 2's
    ``dtc.py`` is still being written.
    """
    try:  # pragma: no cover - exercised only once dtc.py lands
        from gems_t4.gems import dtc as _dtc_mod

        d = _dtc_mod.by_code(code)
        return Dtc(code=d.code, description=d.description, raw=d.raw, state=state)
    except Exception:
        return Dtc(code=code, description=description, raw=raw, state=state)


class _BaseScenario:
    """Shared implementation base for the concrete scenarios."""

    name: str = "base"

    def stored_dtcs(self) -> list[Dtc]:  # pragma: no cover - overridden
        return []

    def perturb(self, state: dict) -> None:  # pragma: no cover - overridden
        return None

    def blocks_actuator(self, actuator_id: int) -> bool:
        return False


class HealthyScenario(_BaseScenario):
    """A fully healthy vehicle: no DTCs, nominal live data, all tests allowed."""

    name = "healthy"

    def stored_dtcs(self) -> list[Dtc]:
        return []

    def perturb(self, state: dict) -> None:
        # Nominal vehicle — leave the baseline state untouched.
        return None

    def blocks_actuator(self, actuator_id: int) -> bool:
        return False


class CoolantSensorScenario(_BaseScenario):
    """Coolant temperature sensor high input (open circuit).

    Symptoms (coherent):
    * DTC **P0118** — Engine Coolant Temperature Circuit High Input.
    * Live coolant temperature jumps to its fail-safe substitution. An open
      ECT circuit reads as maximum sensor voltage, which the ECU interprets as
      an implausibly cold ``-40 degC``; GEMS then substitutes a fixed fail-safe
      value so the engine can still run. We surface the raw implausible reading
      so the technician can see *why* the code set.
    """

    name = "coolant_sensor"

    #: The implausible reading an open ECT circuit produces (degC).
    FAILSAFE_COOLANT_C = -40.0

    def stored_dtcs(self) -> list[Dtc]:
        return [
            _dtc(
                "P0118",
                "Engine Coolant Temperature Circuit High Input",
                raw=0x0118,
            )
        ]

    def perturb(self, state: dict) -> None:
        # Open circuit -> max voltage -> implausibly cold reading.
        state["coolant_temp"] = self.FAILSAFE_COOLANT_C
        # A cold-reading ECT makes the ECU over-fuel: idle hunts a little high.
        state["rpm"] = max(state.get("rpm", 0.0), 900.0) if state.get("engine_running") else state.get("rpm", 0.0)

    def blocks_actuator(self, actuator_id: int) -> bool:
        return False


class MisfireCyl3Scenario(_BaseScenario):
    """Cylinder-3 misfire.

    Symptoms (coherent):
    * DTC **P0303** — Cylinder 3 Misfire Detected (generic), plus the GEMS
      manufacturer-specific **P1303** for the same cylinder.
    * Live data: elevated per-cylinder misfire count on cylinder 3, slightly
      rough/low idle, and the O2/fuel-trim wobble a real misfire produces.
    """

    name = "misfire_cyl3"

    def stored_dtcs(self) -> list[Dtc]:
        return [
            _dtc("P0303", "Cylinder 3 Misfire Detected", raw=0x0303),
            _dtc("P1303", "Cylinder 3 Misfire (manufacturer specific)", raw=0x1303),
        ]

    def perturb(self, state: dict) -> None:
        # Per-cylinder misfire counter (1-indexed cylinders).
        counts = state.setdefault("misfire_counts", [0] * 8)
        if isinstance(counts, list) and len(counts) >= 3:
            counts[2] = max(counts[2], 25)  # cylinder 3
        state["misfire_total"] = state.get("misfire_total", 0) + 25
        # A dead-ish cylinder drops and roughens idle.
        if state.get("engine_running"):
            state["rpm"] = min(state.get("rpm", 750.0), 680.0)
        # Unburnt O2 reaching the sensor skews it lean-looking.
        state["o2_voltage"] = 0.1

    def blocks_actuator(self, actuator_id: int) -> bool:
        return False


class LambdaHeaterScenario(_BaseScenario):
    """Upstream oxygen-sensor heater open circuit.

    Symptoms (coherent):
    * DTC **P1185** — O2 Sensor Heater Circuit (upstream), from the GEMS
      P1185-P1190 upstream-heater family.
    * Live data: the O2 sensor stays cold, so closed-loop fuelling never
      activates — loop status reports **open loop** and the O2 voltage sits
      inactive.
    * The **O2 heater actuator test is refused/failed** because the heater
      circuit is open — this is the actuator-refusal that ties back to the DTC.
    """

    name = "lambda_heater"

    def stored_dtcs(self) -> list[Dtc]:
        return [
            _dtc(
                "P1185",
                "O2 Sensor Heater Circuit (upstream, bank 1)",
                raw=0x1185,
            )
        ]

    def perturb(self, state: dict) -> None:
        # Cold sensor -> no closed loop.
        state["loop_status"] = "open"
        state["o2_heater_ok"] = False
        # An inactive/cold O2 sensor floats near its bias voltage.
        state["o2_voltage"] = 0.45

    def blocks_actuator(self, actuator_id: int) -> bool:
        # The open heater circuit means the heater test cannot succeed.
        return actuator_id == ACT_O2_HEATER


#: Registry of the built-in scenarios, keyed by their ``name``.
SCENARIOS: dict[str, Scenario] = {
    s.name: s
    for s in (
        HealthyScenario(),
        CoolantSensorScenario(),
        MisfireCyl3Scenario(),
        LambdaHeaterScenario(),
    )
}


def get_scenario(name: str) -> Scenario:
    """Look up a scenario by name, raising ``KeyError`` with a helpful message."""
    try:
        return SCENARIOS[name]
    except KeyError:
        raise KeyError(
            f"unknown scenario {name!r}; choose from {sorted(SCENARIOS)}"
        ) from None
