"""Independent regression tests: the virtual GEMS ECU state machine.

Written from the frozen contract (INTERFACES.md), CLAUDE.md and
RELEASE_NOTES.md — NOT derived from the original tests/ suite.

Covers: service dispatch (session, tester-present, $21 reads, unsupported
SID/id negatives, $1A identification), the sim clock (engine run time,
warm-up curve, idle hunt), SecurityAccess seed/key, and the ECU-side
immobilised flag ($31 status routine + $61 id 0x1A).
"""
from __future__ import annotations

import pytest

from gems_t4.gems import immobiliser as immo
from gems_t4.gems import livedata
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.protocol.messages import NRC, NegativeResponse, Request
from gems_t4.protocol.security import compute_key
from gems_t4.transport.virtual import VirtualTransport


def make_stack(scenario: str = "healthy", **ecu_kwargs):
    """Build the in-process VirtualEcu -> VirtualTransport -> KwpClient stack."""
    ecu = VirtualEcu(get_scenario(scenario), **ecu_kwargs)
    client = KwpClient(VirtualTransport(ecu))
    client.connect()
    return ecu, client


def read_value(client: KwpClient, local_id: int):
    """Read one $61 measure and return its decoded engineering value."""
    raw = client.read_data_by_local_id(local_id)
    return livedata.decode_measure(local_id, raw).value


# --------------------------------------------------------------------------- #
# Basic service dispatch
# --------------------------------------------------------------------------- #

def test_start_session_echoes_session_byte():
    _, client = make_stack()
    resp = client.start_session(0x81)
    assert not resp.is_negative
    assert resp.data == bytes([0x81])


def test_tester_present_positive():
    _, client = make_stack()
    # Contract: TesterPresent (0x3E) answers an empty positive response.
    client.tester_present()  # raises on a negative response


def test_read_known_local_id_echoes_id_and_value():
    _, client = make_stack()
    resp = client.request(Request(0x21, bytes([0x01])), expect_positive=True)
    assert resp.data[0] == 0x01
    # value bytes follow the echoed id (coolant temp is a 1-byte param)
    assert len(resp.data) == 1 + livedata.PARAMETERS[0x01].nbytes


def test_unsupported_local_id_answers_negative_out_of_range():
    """Per INTERFACES.md: unsupported localId -> negative REQUEST_OUT_OF_RANGE
    (the '$7f' answer the T4 stylization documents for unsupported ids)."""
    _, client = make_stack()
    with pytest.raises(NegativeResponse) as exc:
        client.read_data_by_local_id(0x1E)  # gap between 0x1D and 0x20
    assert exc.value.nrc == NRC.REQUEST_OUT_OF_RANGE
    assert exc.value.service == 0x21


def test_unsupported_sid_answers_service_not_supported():
    ecu = VirtualEcu()
    resp = ecu.handle(Request(0x99))
    assert resp.is_negative
    assert resp.nrc == NRC.SERVICE_NOT_SUPPORTED


def test_read_ecu_identification():
    _, client = make_stack()
    resp = client.request(Request(0x1A, bytes([0x00])), expect_positive=True)
    assert resp.data[0] == 0x00
    assert b"GEMS" in resp.data[1:]


# --------------------------------------------------------------------------- #
# Sim clock: engine run time, warm-up curve, idle hunt
# --------------------------------------------------------------------------- #

def test_engine_run_time_follows_sim_clock():
    """$61 id 0x1D is fed from the sim clock while the engine runs
    (RELEASE_NOTES.md: 'Engine run time (s, fed from sim clock)')."""
    ecu, client = make_stack()
    assert read_value(client, 0x1D) == 0
    ecu.tick(2.0)
    ecu.tick(3.0)
    assert read_value(client, 0x1D) == 5


def test_engine_run_time_holds_when_engine_stops():
    ecu, client = make_stack()
    ecu.tick(4.0)
    assert read_value(client, 0x1D) == 4
    ecu.state["engine_running"] = False
    ecu.tick(10.0)
    assert read_value(client, 0x1D) == 4  # holds its last value


def test_warm_up_curve_coolant_rises_and_plateaus():
    """The contract documents a warm-up curve advanced by tick()."""
    ecu, client = make_stack()
    ecu.state["coolant_temp"] = 20.0
    readings = []
    for _ in range(30):
        ecu.tick(1.0)
        readings.append(read_value(client, 0x01))
    assert readings[0] > 20  # it rises
    assert all(b >= a for a, b in zip(readings, readings[1:]))  # monotonic
    assert readings[-1] == 88  # plateaus at operating temperature


def test_idle_hunt_keeps_rpm_near_idle_target():
    ecu, client = make_stack()
    for dt in (0.7, 1.3, 2.1, 0.4):
        ecu.tick(dt)
        rpm = read_value(client, 0x02)
        assert 700 <= rpm <= 800  # hunts around the 750 rpm idle target


# --------------------------------------------------------------------------- #
# SecurityAccess (0x27)
# --------------------------------------------------------------------------- #

def test_security_access_seed_key_flow():
    _, client = make_stack()
    client.security_access(compute_key)  # raises if the ECU rejects the key


def test_security_access_wrong_key_rejected():
    _, client = make_stack()
    seed_resp = client.request(Request(0x27, bytes([0x01])), expect_positive=True)
    seed = (seed_resp.data[1] << 8) | seed_resp.data[2]
    bad_key = (compute_key(seed) ^ 0xFFFF) & 0xFFFF
    resp = client.request(
        Request(0x27, bytes([0x02, (bad_key >> 8) & 0xFF, bad_key & 0xFF]))
    )
    assert resp.is_negative
    assert resp.nrc == NRC.INVALID_KEY


# --------------------------------------------------------------------------- #
# Immobilised flag (ECU-side only; full workflow belongs to another suite)
# --------------------------------------------------------------------------- #

def test_default_ecu_is_mobilised():
    _, client = make_stack()
    status = immo.read_status(client)
    assert status.mobilised is True
    assert status.learn_mode is False
    assert read_value(client, 0x1A) == 1  # $61 'Immobiliser mobilised'


def test_immobilised_flag_reports_engine_immobilised():
    """VirtualEcu(immobilised=True) starts desynced — the canon
    'ENGINE IMMOBILISED' state, visible via the $31 status routine."""
    _, client = make_stack(immobilised=True)
    resp = client.start_routine(immo.ROUTINE_STATUS, expect_positive=True)
    assert resp.data[0] == immo.ROUTINE_STATUS
    assert resp.data[1] == 0  # not mobilised
    status = immo.read_status(client)
    assert status.mobilised is False
    assert status.summary == "ENGINE IMMOBILISED"
    # The $61 mirror param agrees with the routine.
    assert read_value(client, 0x1A) == 0


def test_enter_learn_without_security_access_is_denied():
    _, client = make_stack(immobilised=True)
    resp = client.start_routine(immo.ROUTINE_ENTER_LEARN)
    assert resp.is_negative
    assert resp.nrc == NRC.SECURITY_ACCESS_DENIED
