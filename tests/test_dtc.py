"""DTC table + 0x18 payload encode/decode."""
from __future__ import annotations

from gems_t4.gems import dtc
from gems_t4.gems.types import DtcState


def test_table_keyed_by_raw_and_reverse_lookup():
    d = dtc.by_code("P0118")
    assert dtc.DTC_TABLE[d.raw] is d
    assert d.code == "P0118"


def test_encode_decode_round_trip():
    dtcs = [
        dtc.make_dtc("P0118", DtcState.ACTIVE),
        dtc.make_dtc("P0303", DtcState.STORED),
    ]
    payload = dtc.encode_dtc_response(dtcs)
    decoded = dtc.decode_dtc_response(payload)
    assert [d.code for d in decoded] == ["P0118", "P0303"]
    assert decoded[0].state == DtcState.ACTIVE


def test_empty_payload_is_no_faults():
    assert dtc.decode_dtc_response(b"\x00") == []


def test_only_gems_era_codes_present():
    # A 99MY+ Thor/Disco2 code must NOT be in the table.
    assert "P0600" not in {d.code for d in dtc.DTC_TABLE.values()}
