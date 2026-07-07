"""GEMS actuator (output) tests, with the characterful refusal interlocks.

The documented GEMS "Outputs" are simple on/off toggles: MIL, O2 sensor heater,
fuel pump relay, A/C grant, condenser fan (see gems-data-catalog.md). The fuel
pump relay is marked ``allowed_engine_running=False`` so the virtual ECU refuses
it while the engine runs — the authentic "Test not available — engine running"
behaviour, surfaced here as a negative response turned into an
:class:`~gems_t4.gems.types.ActuatorOutcome`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from gems_t4.gems.types import ActuatorOutcome
from gems_t4.protocol.messages import NRC

if TYPE_CHECKING:  # pragma: no cover
    from gems_t4.protocol.client import KwpClient

STATE_OFF = 0x00
STATE_ON = 0x01


@dataclass(frozen=True, slots=True)
class ActuatorDef:
    """One actuator output test."""

    actuator_id: int
    name: str
    allowed_engine_running: bool = True


ACT_MIL = 0x01
ACT_O2_HEATER = 0x02
ACT_FUEL_PUMP = 0x03
ACT_AC_GRANT = 0x04
ACT_CONDENSER_FAN = 0x05

_DEFS: tuple[ActuatorDef, ...] = (
    ActuatorDef(ACT_MIL, "Malfunction indicator lamp (MIL)", True),
    ActuatorDef(ACT_O2_HEATER, "Oxygen sensor heater", True),
    ActuatorDef(ACT_FUEL_PUMP, "Fuel pump relay", False),  # refused while running
    ActuatorDef(ACT_AC_GRANT, "Air conditioning grant", True),
    ActuatorDef(ACT_CONDENSER_FAN, "Condenser fan relay", True),
)

#: All actuators keyed by id.
ACTUATORS: dict[int, ActuatorDef] = {a.actuator_id: a for a in _DEFS}

#: Convenience: look an actuator up by (case-insensitive) short name token.
_BY_NAME: dict[str, ActuatorDef] = {
    "mil": ACTUATORS[ACT_MIL],
    "o2_heater": ACTUATORS[ACT_O2_HEATER],
    "fuel_pump": ACTUATORS[ACT_FUEL_PUMP],
    "ac_grant": ACTUATORS[ACT_AC_GRANT],
    "condenser_fan": ACTUATORS[ACT_CONDENSER_FAN],
}


def by_name(token: str) -> ActuatorDef:
    """Look up an actuator by its short token (e.g. ``"fuel_pump"``)."""
    try:
        return _BY_NAME[token.lower()]
    except KeyError:
        raise KeyError(
            f"unknown actuator {token!r}; choose from {sorted(_BY_NAME)}"
        ) from None


def run(client: "KwpClient", actuator_id: int, state: int) -> ActuatorOutcome:
    """Command an actuator test and return the outcome.

    A negative response (e.g. CONDITIONS_NOT_CORRECT while the engine runs) is
    reported as ``ok=False`` with a human-readable message rather than raised.
    """
    resp = client.actuator(actuator_id, state)
    act = ACTUATORS.get(actuator_id)
    label = act.name if act else f"actuator 0x{actuator_id:02X}"
    if resp.is_negative:
        if resp.nrc == NRC.CONDITIONS_NOT_CORRECT:
            msg = f"{label}: test not available — conditions not correct"
        else:
            msg = f"{label}: refused ({resp.nrc_name})"
        return ActuatorOutcome(actuator_id=actuator_id, ok=False, message=msg)
    verb = "on" if state == STATE_ON else "off"
    return ActuatorOutcome(
        actuator_id=actuator_id, ok=True, message=f"{label}: switched {verb}"
    )
