"""Independent regression tests: the $61 live-data catalogue and actuator tests.

Written from the frozen contract (INTERFACES.md), CLAUDE.md and
RELEASE_NOTES.md — NOT derived from the original tests/ suite.

Documented claims under test:
* exactly 37 $61 parameters, including the v0.0.3 additions
  (0x17 injector PW, 0x18 coil charge, 0x1B purge duty, 0x1C fuel pump,
  0x1D engine run time, 0x20-0x27 per-cylinder misfire counts);
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

def test_exactly_37_parameters():
    """RELEASE_NOTES.md v0.0.3: '24 -> 37 $61 measures'."""
    assert len(livedata.PARAMETERS) == 37


def test_parameter_id_layout():
    """Contiguous 0x01..0x1D block plus the 0x20..0x27 per-cylinder block."""
    expected = set(range(0x01, 0x1E)) | set(range(0x20, 0x28))
    assert set(livedata.PARAMETERS) == expected


@pytest.mark.parametrize(
    "local_id, name_fragment, unit",
    [
        (0x17, "injector pulse width", "ms"),
        (0x18, "coil charge", "ms"),
        (0x1B, "purge", "%"),
        (0x1C, "fuel pump", ""),
        (0x1D, "run time", "s"),
    ],
)
def test_release_notes_new_parameters(local_id, name_fragment, unit):
    p = livedata.PARAMETERS[local_id]
    assert name_fragment in p.name.lower()
    assert p.unit == unit


def test_per_cylinder_misfire_params_are_one_byte():
    """0x20-0x27 misfire counts, cylinders 1-8, 1-byte each (saturate at 255)."""
    for cyl, local_id in enumerate(range(0x20, 0x28), start=1):
        p = livedata.PARAMETERS[local_id]
        assert p.nbytes == 1
        assert "misfire" in p.name.lower()
        assert str(cyl) in p.name


@pytest.mark.parametrize(
    "local_id, name_fragment, unit",
    [
        (0x01, "coolant", "degC"),
        (0x02, "engine speed", "rpm"),
        (0x03, "battery", "V"),
        (0x04, "throttle", "%"),
        (0x05, "air flow", "kg/h"),
        (0x07, "o2 sensor", "V"),
        (0x0A, "idle air", "steps"),
        (0x0F, "fuel temperature", "degC"),
    ],
)
def test_common_ids_from_the_docs(local_id, name_fragment, unit):
    p = livedata.PARAMETERS[local_id]
    assert name_fragment in p.name.lower()
    assert p.unit == unit


# --------------------------------------------------------------------------- #
# Encode / decode
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "local_id, value",
    [
        (0x01, -40),      # coolant at its offset floor
        (0x01, 88),       # warm coolant
        (0x02, 750),      # rpm, 2-byte, 0.25 scale
        (0x03, 13.8),     # battery, 0.1 scale
        (0x08, -5),       # signed short-term fuel trim
        (0x17, 2.5),      # injector PW ms, 0.01 scale
    ],
)
def test_encode_decode_round_trip(local_id, value):
    p = livedata.PARAMETERS[local_id]
    m = p.decode(p.encode(value))
    assert m.value == pytest.approx(value, abs=p.scale)
    assert m.name == p.name
    assert m.unit == p.unit


def test_one_byte_counter_encode_saturates_at_255():
    p = livedata.PARAMETERS[0x22]  # misfire count cyl 3
    assert p.encode(500) == b"\xff"
    assert p.decode(b"\xff").value == 255


def test_decode_measure_unknown_id_is_generic_not_a_crash():
    m = livedata.decode_measure(0x7E, b"\x12")
    assert "unknown" in m.name.lower()
    assert m.raw == 0x12


def test_read_all_returns_all_37_measures():
    _, client = make_stack()
    measures = livedata.read_all(client)
    assert len(measures) == 37
    names = {m.name for m in measures}
    assert "Coolant temperature" in names


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


def test_o2_heater_works_on_a_healthy_vehicle():
    _, client = make_stack("healthy")
    outcome = act.run(client, act.ACT_O2_HEATER, act.STATE_ON)
    assert outcome.ok is True


def test_unknown_actuator_id_answers_out_of_range():
    _, client = make_stack("healthy")
    resp = client.actuator(0x7E, act.STATE_ON)
    assert resp.is_negative
    assert resp.nrc == NRC.REQUEST_OUT_OF_RANGE
