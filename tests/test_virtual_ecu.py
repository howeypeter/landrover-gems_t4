"""Virtual ECU request handling."""
from __future__ import annotations

from gems_t4.gems import dtc, livedata
from gems_t4.gems.actuators import ACT_FUEL_PUMP, ACT_MIL
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.messages import NRC, Request
from gems_t4.protocol.security import compute_key


def test_session_and_tester_present():
    ecu = VirtualEcu()
    assert not ecu.handle(Request(0x10, b"\x81")).is_negative
    assert not ecu.handle(Request(0x3E)).is_negative


def test_read_coolant_local_id_healthy():
    ecu = VirtualEcu()
    resp = ecu.handle(Request(0x21, b"\x01"))
    assert not resp.is_negative
    assert resp.data[0] == 0x01
    measure = livedata.decode_measure(0x01, resp.data[1:])
    assert 80 <= float(measure.value) <= 90


def test_unsupported_service_negative():
    ecu = VirtualEcu()
    resp = ecu.handle(Request(0x99))
    assert resp.is_negative and resp.nrc == NRC.SERVICE_NOT_SUPPORTED


def test_read_and_clear_dtcs():
    ecu = VirtualEcu(get_scenario("coolant_sensor"))
    payload = ecu.handle(Request(0x18)).data
    codes = [d.code for d in dtc.decode_dtc_response(payload)]
    assert "P0118" in codes
    ecu.handle(Request(0x14))  # clear
    assert dtc.decode_dtc_response(ecu.handle(Request(0x18)).data) == []


def test_fuel_pump_refused_while_running():
    ecu = VirtualEcu()
    assert ecu.state["engine_running"] is True
    resp = ecu.handle(Request(0x30, bytes([ACT_FUEL_PUMP, 0x01])))
    assert resp.is_negative and resp.nrc == NRC.CONDITIONS_NOT_CORRECT


def test_mil_actuator_allowed():
    ecu = VirtualEcu()
    resp = ecu.handle(Request(0x30, bytes([ACT_MIL, 0x01])))
    assert not resp.is_negative


def test_security_handshake():
    ecu = VirtualEcu()
    seed_resp = ecu.handle(Request(0x27, b"\x01"))
    seed = (seed_resp.data[1] << 8) | seed_resp.data[2]
    key = compute_key(seed)
    ok = ecu.handle(Request(0x27, bytes([0x02, key >> 8, key & 0xFF])))
    assert not ok.is_negative
    bad = ecu.handle(Request(0x27, bytes([0x02, 0x00, 0x00])))
    assert bad.is_negative and bad.nrc == NRC.INVALID_KEY


def test_tick_warms_coolant_over_time():
    ecu = VirtualEcu()
    ecu.state["coolant_temp"] = 20.0
    for _ in range(50):
        ecu.tick(0.1)
    assert float(ecu.state["coolant_temp"]) > 20.0


def test_all_live_ids_answer_with_nominals():
    # Every $61 parameter must answer positively; a fresh healthy ECU should
    # decode straight back to its own nominal (within one LSB of the scale).
    ecu = VirtualEcu()
    for local_id, p in livedata.PARAMETERS.items():
        resp = ecu.handle(Request(0x21, bytes([local_id])))
        assert not resp.is_negative, f"id 0x{local_id:02X} refused"
        assert resp.data[0] == local_id
        m = livedata.decode_measure(local_id, resp.data[1:])
        if isinstance(p.nominal, (int, float)):
            assert abs(float(m.value) - float(p.nominal)) <= p.scale + 1e-9


def test_run_time_tracks_sim_clock():
    ecu = VirtualEcu()
    for _ in range(20):
        ecu.tick(0.5)  # 10 s of sim time
    resp = ecu.handle(Request(0x21, b"\x1d"))
    assert not resp.is_negative
    assert livedata.decode_measure(0x1D, resp.data[1:]).value == 10


def test_misfire_scenario_counts_climb_on_cylinder_3_only():
    ecu = VirtualEcu(get_scenario("misfire_cyl3"))
    ecu.tick(0.1)
    ecu.tick(0.1)

    def read(lid: int) -> float:
        resp = ecu.handle(Request(0x21, bytes([lid])))
        assert not resp.is_negative
        return float(livedata.decode_measure(lid, resp.data[1:]).value)

    cyl3 = read(0x22)
    assert cyl3 > 0
    # one-byte counter saturates at 255; the running total keeps climbing
    assert cyl3 == min(255, float(ecu.state["misfire_total"]))
    for lid in (0x20, 0x21, 0x23, 0x24, 0x25, 0x26, 0x27):
        assert read(lid) == 0
