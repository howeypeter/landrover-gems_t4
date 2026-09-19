"""Independent regression tests: the $61 live-data catalogue and actuator tests.

Written from the frozen contract (INTERFACES.md), CLAUDE.md and
RELEASE_NOTES.md — NOT derived from the original tests/ suite.

Documented claims under test:
* exactly 40 $61 parameters, including the v0.0.3 additions
  (0x17 injector PW, 0x18 coil charge, 0x1B purge duty, 0x1C fuel pump,
  0x1D engine run time, 0x20-0x27 per-cylinder misfire counts) and the
  2026-07-11 additions (0x1E oil temp, 0x1F catalyst temp, 0x28 cooling fan);
* the common ids from the docs (0x01 coolant, 0x02 rpm, 0x03 battery,
  0x04 throttle, 0x05 MAF, 0x07 O2 bank A, 0x0A IACV steps, 0x0F fuel temp);
* encode/decode round trips and 1-byte saturation at 255;
* the five actuator tokens and their characterful refusal interlocks.
"""
from __future__ import annotations

import pytest

from gems_t4.gems import actuators as act
from gems_t4.gems import dtc as dtc_mod
from gems_t4.gems import livedata
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.types import Dtc, DtcState
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.protocol.messages import NRC
from gems_t4.transport.virtual import VirtualTransport


def make_stack(scenario: str = "healthy", **ecu_kwargs):
    ecu = VirtualEcu(get_scenario(scenario), **ecu_kwargs)
    client = KwpClient(VirtualTransport(ecu))
    client.connect()
    return ecu, client


# --------------------------------------------------------------------------- #
# The parameter catalogue
# --------------------------------------------------------------------------- #

def test_exactly_40_parameters():
    """37 (v0.0.3) + 3 (2026-07-11: oil temp, catalyst temp, cooling fan)."""
    assert len(livedata.PARAMETERS) == 40


def test_parameter_id_layout():
    """Confirmed sensors carry their real GEMS $21 local ids (bench-mapped, see
    docs/rave-cross-reference.md); emulator-only values sit in a synthetic
    0x40+ block, and nothing collides with the coding block (0x81+)."""
    real = {
        "coolant_temp": 0x00, "intake_air_temp": 0x01, "ac_request": 0x06,
        "throttle": 0x10, "maf": 0x11, "fuel_temp": 0x15,
        "o2_voltage": 0x18, "o2_voltage_b2": 0x19,
    }
    for key, lid in real.items():
        assert livedata.BY_STATE_KEY[key].local_id == lid
    # emulator-only values (no confirmed $21 id) live at 0x40+
    assert livedata.BY_STATE_KEY["rpm"].local_id >= 0x40
    # no live id treads on the coding block
    assert all(lid < 0x81 for lid in livedata.PARAMETERS)


@pytest.mark.parametrize(
    "state_key, name_fragment, unit",
    [
        ("injector_pw", "injector pulse width", "ms"),
        ("coil_charge", "coil charge", "ms"),
        ("purge_duty", "purge", "%"),
        ("fuel_pump", "fuel pump", ""),
        ("run_time", "run time", "s"),
    ],
)
def test_release_notes_new_parameters(state_key, name_fragment, unit):
    p = livedata.BY_STATE_KEY[state_key]
    assert name_fragment in p.name.lower()
    assert p.unit == unit


def test_per_cylinder_misfire_params_are_one_byte():
    """Misfire counts, cylinders 1-8, 1-byte each (saturate at 255)."""
    for cyl in range(1, 9):
        p = livedata.BY_STATE_KEY[f"misfire_cyl{cyl}"]
        assert p.nbytes == 1
        assert "misfire" in p.name.lower()
        assert str(cyl) in p.name


@pytest.mark.parametrize(
    "state_key, name_fragment, unit",
    [
        ("coolant_temp", "coolant", "degC"),
        ("rpm", "engine speed", "rpm"),
        ("battery", "battery", "V"),
        ("throttle", "throttle", "%"),
        ("maf", "air flow", "kg/h"),
        ("o2_voltage", "o2 sensor", "V"),
        ("iacv_steps", "idle air", "steps"),
        ("fuel_temp", "fuel temperature", "degC"),
    ],
)
def test_common_ids_from_the_docs(state_key, name_fragment, unit):
    p = livedata.BY_STATE_KEY[state_key]
    assert name_fragment in p.name.lower()
    assert p.unit == unit


# --------------------------------------------------------------------------- #
# Encode / decode
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "state_key, value",
    [
        ("coolant_temp", -40),   # coolant at its offset floor
        ("coolant_temp", 88),    # warm coolant
        ("rpm", 750),            # rpm, 2-byte, 0.25 scale
        ("battery", 13.8),       # battery, 0.1 scale
        ("fuel_trim_short", -5), # signed short-term fuel trim
        ("injector_pw", 2.5),    # injector PW ms, 0.01 scale
    ],
)
def test_encode_decode_round_trip(state_key, value):
    p = livedata.BY_STATE_KEY[state_key]
    m = p.decode(p.encode(value))
    assert m.value == pytest.approx(value, abs=p.scale)
    assert m.name == p.name
    assert m.unit == p.unit


def test_one_byte_counter_encode_saturates_at_255():
    p = livedata.BY_STATE_KEY["misfire_cyl3"]  # per-cyl misfire counter
    assert p.encode(500) == b"\xff"
    assert p.decode(b"\xff").value == 255


def test_decode_measure_unknown_id_is_generic_not_a_crash():
    m = livedata.decode_measure(0x7E, b"\x12")
    assert "unknown" in m.name.lower()
    assert m.raw == 0x12


def test_read_all_returns_all_40_measures():
    _, client = make_stack()
    measures = livedata.read_all(client)
    assert len(measures) == 40
    names = {m.name for m in measures}
    assert "Coolant temperature" in names
    assert "Oil temperature" in names
    assert "Catalyst temperature (bank A)" in names
    assert "Cooling fan state" in names


# --------------------------------------------------------------------------- #
# DTC payload encode/decode (shared by ECU and client sides)
# --------------------------------------------------------------------------- #

def test_dtc_payload_round_trip():
    dtcs = [
        dtc_mod.make_dtc("P0118", DtcState.ACTIVE),
        dtc_mod.make_dtc("P1185", DtcState.STORED),
    ]
    out = dtc_mod.decode_dtc_response(dtc_mod.encode_dtc_response(dtcs))
    assert [(d.code, d.state) for d in out] == [
        ("P0118", DtcState.ACTIVE),
        ("P1185", DtcState.STORED),
    ]


def test_empty_dtc_payload_decodes_to_no_faults():
    assert dtc_mod.decode_dtc_response(dtc_mod.encode_dtc_response([])) == []
    assert dtc_mod.decode_dtc_response(b"") == []


def test_unknown_raw_dtc_is_surfaced_not_crashed():
    payload = bytes([1, 0xEE, 0xEE, 0x24])
    (d,) = dtc_mod.decode_dtc_response(payload)
    assert d.code == "P----"
    assert d.raw == 0xEEEE


# --------------------------------------------------------------------------- #
# Actuators: the token set and the characterful refusals
# --------------------------------------------------------------------------- #

def test_exactly_five_actuator_tokens():
    """CLAUDE.md/INTERFACES.md: MIL, O2 heater, fuel pump relay, A/C grant,
    condenser fan — addressed by these short tokens."""
    tokens = {"ac_grant", "condenser_fan", "fuel_pump", "mil", "o2_heater"}
    assert {t.lower() for t in act._BY_NAME} == tokens
    assert len(act.ACTUATORS) == 5
    for token in tokens:
        assert act.by_name(token).actuator_id in act.ACTUATORS


def test_by_name_unknown_token_raises():
    with pytest.raises(KeyError):
        act.by_name("ecu_self_destruct")


def test_fuel_pump_refused_while_engine_running():
    """The virtual ECU defaults to an idling engine, so the fuel-pump test is
    the authentic 'test not available' refusal (CONDITIONS_NOT_CORRECT)."""
    _, client = make_stack("healthy")
    outcome = act.run(client, act.ACT_FUEL_PUMP, act.STATE_ON)
    assert outcome.ok is False
    assert "test not available" in outcome.message.lower()
    # The engine-running-sensitive actuator names the specific reason.
    assert "engine is running" in outcome.message.lower()


def test_fuel_pump_allowed_with_engine_stopped():
    ecu, client = make_stack("healthy")
    ecu.state["engine_running"] = False
    outcome = act.run(client, act.ACT_FUEL_PUMP, act.STATE_ON)
    assert outcome.ok is True


def test_mil_test_works_with_engine_running():
    _, client = make_stack("healthy")
    on = act.run(client, act.ACT_MIL, act.STATE_ON)
    off = act.run(client, act.ACT_MIL, act.STATE_OFF)
    assert on.ok and off.ok
    assert "on" in on.message.lower()


def test_o2_heater_refused_under_lambda_heater_scenario():
    """The open heater circuit (P1185) makes the O2-heater test refuse —
    the actuator refusal that ties back to the DTC."""
    _, client = make_stack("lambda_heater")
    outcome = act.run(client, act.ACT_O2_HEATER, act.STATE_ON)
    assert outcome.ok is False
    assert "test not available" in outcome.message.lower()
    # A different reason keeps the generic wording (not the engine-running one).
    assert "conditions not correct" in outcome.message.lower()
    assert "engine is running" not in outcome.message.lower()


def test_o2_heater_works_on_a_healthy_vehicle():
    _, client = make_stack("healthy")
    outcome = act.run(client, act.ACT_O2_HEATER, act.STATE_ON)
    assert outcome.ok is True


def test_unknown_actuator_id_answers_out_of_range():
    _, client = make_stack("healthy")
    resp = client.actuator(0x7E, act.STATE_ON)
    assert resp.is_negative
    assert resp.nrc == NRC.REQUEST_OUT_OF_RANGE
