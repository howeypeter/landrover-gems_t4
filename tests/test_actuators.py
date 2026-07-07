"""Actuator run() outcomes, including the engine-running refusal."""
from __future__ import annotations

from gems_t4.gems import actuators
from gems_t4.protocol.messages import NRC, Request, Response


class _FakeClient:
    def __init__(self, responder):
        self._responder = responder

    def actuator(self, actuator_id: int, state: int) -> Response:
        return self._responder(actuator_id, state)


def test_positive_actuator_is_ok():
    client = _FakeClient(lambda aid, st: Response.positive(0x30, bytes([aid, st])))
    outcome = actuators.run(client, actuators.ACT_MIL, actuators.STATE_ON)
    assert outcome.ok
    assert "on" in outcome.message


def test_conditions_not_correct_is_refusal():
    client = _FakeClient(
        lambda aid, st: Response.negative(0x30, NRC.CONDITIONS_NOT_CORRECT)
    )
    outcome = actuators.run(client, actuators.ACT_FUEL_PUMP, actuators.STATE_ON)
    assert not outcome.ok
    assert "not available" in outcome.message


def test_by_name_and_fuel_pump_flag():
    assert actuators.by_name("fuel_pump").actuator_id == actuators.ACT_FUEL_PUMP
    assert actuators.ACTUATORS[actuators.ACT_FUEL_PUMP].allowed_engine_running is False
