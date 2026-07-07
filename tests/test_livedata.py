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
