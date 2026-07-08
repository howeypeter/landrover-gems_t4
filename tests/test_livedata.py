"""Live-data param encode/decode round-trips."""
from __future__ import annotations

from gems_t4.gems import livedata


def test_all_numeric_params_round_trip():
    for p in livedata.PARAMETERS.values():
        if not isinstance(p.nominal, (int, float)):
            continue
        raw = p.encode(float(p.nominal))
        m = p.decode(raw)
        # decoded value should be within one LSB (scale) of the input
        assert abs(float(m.value) - float(p.nominal)) <= p.scale + 1e-9
        assert len(raw) == p.nbytes


def test_coolant_offset_encoding():
    coolant = livedata.PARAMETERS[0x01]
    raw = coolant.encode(85.0)
    assert raw == bytes([125])  # 85 + 40 offset
    assert coolant.decode(raw).value == 85


def test_rpm_two_byte_scale():
    rpm = livedata.PARAMETERS[0x02]
    raw = rpm.encode(750.0)
    assert len(raw) == 2
    assert rpm.decode(raw).value == 750


def test_encode_clamps_out_of_range():
    coolant = livedata.PARAMETERS[0x01]
    # Absurdly high value must clamp to a valid single byte, not raise.
    raw = coolant.encode(100000.0)
    assert len(raw) == 1


def test_decode_measure_unknown_id():
    m = livedata.decode_measure(0xFE, b"\x12")
    assert "Unknown" in m.name


def test_parameter_count_and_unique_state_keys():
    # Phase 6 expansion: 24 originals + 13 new (0x17, 0x18, 0x1B-0x1D, 0x20-0x27).
    assert len(livedata.PARAMETERS) == 37
    keys = [p.state_key for p in livedata.PARAMETERS.values()]
    assert len(keys) == len(set(keys))


def test_injector_pulse_width_two_byte_centiseconds():
    pw = livedata.PARAMETERS[0x17]
    raw = pw.encode(2.5)
    assert len(raw) == 2
    assert raw == bytes([0x00, 0xFA])  # 2.5 ms / 0.01 = 250
    assert pw.decode(raw).value == 2.5


def test_per_cylinder_misfire_ids_and_state_keys():
    for cyl in range(1, 9):
        p = livedata.PARAMETERS[0x20 + cyl - 1]
        assert p.state_key == f"misfire_cyl{cyl}"
        assert p.nbytes == 1
        assert p.decode(p.encode(0)).value == 0
        # a saturating counter clamps rather than raising
        assert p.encode(9999) == b"\xff"


def test_engine_run_time_two_bytes():
    rt = livedata.PARAMETERS[0x1D]
    raw = rt.encode(3600)
    assert len(raw) == 2
    assert rt.decode(raw).value == 3600
