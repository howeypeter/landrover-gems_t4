"""Tests for the K-line ISO 9141-2 / OBD-II profile (gems_t4.protocol.kline).

The response frames here are the *real bytes* captured from a physical P38
GEMS ECU during first-light bring-up (2026-08), so these tests pin the decode
path to hardware truth, not a model.
"""
from __future__ import annotations

import pytest

from gems_t4.protocol import kline
from gems_t4.transport.base import InitResult, Transport, TransportTimeout


class FakeKlineEcu(Transport):
    """A transport that replays canned OBD responses keyed by request payload.

    ``responses`` maps a request payload hex (the bytes after the 68 6A F1
    header, before the checksum) to a full response frame. A missing key means
    the ECU stays silent -> TransportTimeout (e.g. Mode 03 with no codes).
    """

    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self._pending: bytes | None = None
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def init(self, address: int, mode: str = "slow") -> InitResult:
        assert address == kline.KLINE_INIT_ADDRESS
        return InitResult()

    def send(self, frame: bytes) -> None:
        payload = frame[3:-1]  # strip 68 6A F1 header + checksum
        resp = self.responses.get(payload.hex())
        if resp is None:
            raise TransportTimeout("silent ECU")
        self._pending = resp

    def receive(self, timeout: float | None = None) -> bytes:
        if self._pending is None:
            raise TransportTimeout("no buffered response")
        frame, self._pending = self._pending, None
        return frame


# Real captured frames.
PID00 = bytes.fromhex("486be84100bf9ff991c4")  # supported PIDs 01-20
PID05 = bytes.fromhex("486be8410500e1")        # coolant = 0x00 -> -40 C
RESPONSES = {"0100": PID00, "0105": PID05}


def test_encode_request_header_and_checksum() -> None:
    frame = kline.encode_request(b"\x01\x05")
    assert frame[:3] == bytes([0x68, 0x6A, 0xF1])
    assert frame[3:5] == b"\x01\x05"
    assert frame[-1] == (0x68 + 0x6A + 0xF1 + 0x01 + 0x05) & 0xFF


def test_decode_response_strips_header_and_checksum() -> None:
    assert kline.decode_response(PID05) == bytes.fromhex("410500")


def test_decode_response_rejects_bad_checksum() -> None:
    bad = PID05[:-1] + bytes([0x00])
    with pytest.raises(kline.KlineError):
        kline.decode_response(bad)


def test_decode_response_rejects_bad_header() -> None:
    with pytest.raises(kline.KlineError):
        kline.decode_response(bytes.fromhex("00" + PID05.hex()[2:]))


def test_supported_pids_parses_bitmask() -> None:
    client = kline.KlineClient(FakeKlineEcu(RESPONSES))
    client.connect()
    supported = client.supported_pids()
    assert {0x01, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08} <= supported
    assert 0x02 not in supported  # 0xbf bit for PID 2 is clear


def test_supported_pids_is_cached() -> None:
    ecu = FakeKlineEcu(RESPONSES)
    client = kline.KlineClient(ecu)
    client.connect()
    first = client.supported_pids()
    ecu.responses = {}  # a second query would now fail
    assert client.supported_pids() == first  # served from cache


def test_read_pid_decodes_coolant() -> None:
    client = kline.KlineClient(FakeKlineEcu(RESPONSES))
    client.connect()
    assert client.read_pid(0x05) == b"\x00"


def test_read_live_decodes_only_supported() -> None:
    client = kline.KlineClient(FakeKlineEcu(RESPONSES))
    client.connect()
    rows = client.read_live()
    coolant = [r for r in rows if r.pid == 0x05]
    assert len(coolant) == 1
    assert coolant[0].value == -40
    assert coolant[0].unit == "°C"


def test_read_dtcs_empty_when_ecu_silent() -> None:
    # No "03" key -> ECU stays silent -> zero stored codes (the healthy case).
    client = kline.KlineClient(FakeKlineEcu(RESPONSES))
    client.connect()
    assert client.read_dtcs() == []


def test_read_dtcs_decodes_codes() -> None:
    resp = bytes([0x48, 0x6B, 0xE8, 0x43, 0x03, 0x03, 0x11, 0x85])
    resp += bytes([kline.obd_checksum(resp)])
    client = kline.KlineClient(FakeKlineEcu({"03": resp}))
    client.connect()
    assert client.read_dtcs() == ["P0303", "P1185"]


@pytest.mark.parametrize(
    "pair,code",
    [("0303", "P0303"), ("0118", "P0118"), ("1185", "P1185"), ("4321", "C0321")],
)
def test_decode_dtcs_encoding(pair: str, code: str) -> None:
    assert kline.decode_dtcs(bytes.fromhex(pair)) == [code]


def test_decode_dtcs_skips_padding() -> None:
    assert kline.decode_dtcs(bytes.fromhex("03030000")) == ["P0303"]
