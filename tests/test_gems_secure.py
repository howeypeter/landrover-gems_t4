"""Tests for the proprietary 0xDA GEMS channel (SecurityAccess + coding).

The seed→key transform and command map were recovered from the FlemcoDesign
"GEMS ECU Utility" app and confirmed on real hardware 2026-09-08; the key pairs
and captured response frames below are those real values.
"""
from __future__ import annotations

import pytest

from gems_t4.protocol import gems_secure as gs
from gems_t4.transport.base import InitResult, Transport, TransportTimeout


# --- the seed→key transform ------------------------------------------------- #
def test_security_key_confirmed_hardware_pairs():
    # Both captured on the real Disco-1 ECU (da6_unlock / da7_read).
    assert gs.security_key(0xBFC8) == 0xF5D8
    assert gs.security_key(0xF6E8) == 0xF538


def test_security_key_is_16bit_bijection():
    # multiplier is odd ⇒ maps 0..65535 one-to-one onto itself.
    keys = {gs.security_key(s) for s in range(65536)}
    assert len(keys) == 65536
    assert gs.security_key(0) == 0


# --- no-address framing ----------------------------------------------------- #
def test_encode_secure_len_and_checksum():
    # 2701 -> 02 27 01 2A  (len 02, checksum = 02+27+01 = 0x2A)
    assert gs.encode_secure(b"\x27\x01") == bytes.fromhex("022701" "2a")


def test_encode_decode_round_trip():
    for payload in (b"\x10\x02", b"\x22\x04\xE2", b"\x27\x02\xF5\xD8"):
        assert gs.decode_secure(gs.encode_secure(payload)) == payload


def test_decode_rejects_bad_checksum():
    good = bytearray(gs.encode_secure(b"\x22\x04\xE2"))
    good[-1] ^= 0xFF
    with pytest.raises(gs.GemsSecureError):
        gs.decode_secure(bytes(good))


@pytest.mark.parametrize(
    "frame_hex, expected_data",
    [
        ("056204e2409623", "6204e24096"),  # PROM id (23 = frame checksum)
        ("046204bf0029", "6204bf00"),      # config 00 = 4.0 / auto
        ("037f228024", "7f2280"),          # VIN unavailable (negative 7F2280)
    ],
)
def test_decode_secure_real_captured_frames(frame_hex, expected_data):
    assert gs.decode_secure(bytes.fromhex(frame_hex)) == bytes.fromhex(expected_data)


def test_config_byte_decode():
    assert gs.GemsConfig.from_byte(0x00) == gs.GemsConfig(0x00, "4.0", "auto")
    assert gs.GemsConfig.from_byte(0x01).displacement == "4.6"
    assert gs.GemsConfig.from_byte(0x02) == gs.GemsConfig(0x02, "4.6", "manual")
    assert gs.GemsConfig.from_byte(0x03).transmission == "manual"


# --- a scripted fake ECU on the 0xDA channel -------------------------------- #
class FakeSecureEcu(Transport):
    """Emulates the real ECU's 0xDA responses (from the da6/da7 captures)."""

    def __init__(self, seed: int = 0xF6E8) -> None:
        self._open = False
        self._seed = seed
        self._pending: bytes = b""
        self.sent: list[bytes] = []

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def init(self, address: int, mode: str = "slow") -> InitResult:
        assert address == gs.SECURE_INIT_ADDRESS
        return InitResult(keybytes=b"\xAA\x55")

    def send(self, frame: bytes) -> None:
        payload = gs.decode_secure(frame)
        self.sent.append(payload)
        self._pending = gs.encode_secure(self._respond(payload))

    def receive(self, timeout: float | None = None) -> bytes:
        if not self._pending:
            raise TransportTimeout("no scripted reply")
        r, self._pending = self._pending, b""
        return r

    def _respond(self, p: bytes) -> bytes:
        if p == b"\x10\x02":
            return b"\x50\x02"
        if p == b"\x27\x01":
            return b"\x67\x01" + bytes([self._seed >> 8, self._seed & 0xFF])
        if p[:2] == b"\x27\x02":
            key = (p[2] << 8) | p[3]
            return b"\x67\x02\xAA" if key == gs.security_key(self._seed) else b"\x67\x02\xCC"
        if p == b"\x22" + gs.CID_PROM_ID:
            return b"\x62\x04\xE2\x40\x96"
        if p == b"\x22" + gs.CID_CONFIG:
            return b"\x62\x04\xBF\x00"
        if p == b"\x22" + gs.CID_VIN:
            return b"\x7F\x22\x80"           # unavailable on this ECU
        if p == gs.WRITE_RESET_ADAPTIVE or p == gs.WRITE_IMMOBILISER_SYNCH:
            return b"\xE3\x00"               # positive-ish ack
        if p[:1] == b"\x3C" and len(p) == 4:  # memory read: 3C lsb msb len
            return b"\x7C" + bytes([0xAA]) * p[3]
        if p[:1] == b"\x2E":                  # coding write: 2E cid value
            return b"\x6E" + p[1:3]
        return b"\x7F" + p[:1] + b"\x11"     # serviceNotSupported


def test_unlock_succeeds_with_correct_key():
    s = gs.GemsSecureSession(FakeSecureEcu(seed=0xF6E8))
    s.connect()
    assert s.unlock() is True
    assert s.unlocked is True
    assert s.last_seed == 0xF6E8
    # it sent the correctly-computed key
    assert s.transport.sent[-1] == b"\x27\x02" + bytes([0xF5, 0x38])


def test_send_wrong_key_is_rejected():
    # The ECU (fake) computes the real key; sending a deliberately wrong one
    # must return 6702CC -> False, and must NOT unlock.
    s = gs.GemsSecureSession(FakeSecureEcu(seed=0x1234))
    s.connect()
    assert s.start_session()
    seed = s.request_seed()
    assert seed == 0x1234
    wrong = (gs.security_key(seed) ^ 1) & 0xFFFF
    assert s.send_key(wrong) is False
    assert s.unlocked is False


def test_reads_require_unlock():
    s = gs.GemsSecureSession(FakeSecureEcu())
    s.connect()
    with pytest.raises(gs.GemsSecureLocked):
        s.read_prom_id()


def test_authorized_reads_match_hardware():
    s = gs.GemsSecureSession(FakeSecureEcu())
    s.connect()
    assert s.unlock()
    assert s.read_prom_id() == "9640"                 # 40 96 -> byte-swapped
    cfg = s.read_config()
    assert cfg == gs.GemsConfig(0x00, "4.0", "auto")
    assert s.read_vin_last6() is None                 # 7F2280 -> unavailable


def test_writes_gated_then_sent():
    s = gs.GemsSecureSession(FakeSecureEcu())
    s.connect()
    with pytest.raises(gs.GemsSecureLocked):
        s.reset_adaptive_values()
    assert s.unlock()
    s.reset_adaptive_values()
    assert s.transport.sent[-1] == gs.WRITE_RESET_ADAPTIVE
    s.immobiliser_synch()
    assert s.transport.sent[-1] == gs.WRITE_IMMOBILISER_SYNCH


def test_read_memory_framing_and_gate():
    s = gs.GemsSecureSession(FakeSecureEcu())
    s.connect()
    with pytest.raises(gs.GemsSecureLocked):
        s.read_memory(0x2000, 4)
    assert s.unlock()
    assert s.read_memory(0x2000, 4) == b"\xAA\xAA\xAA\xAA"
    # request framing: 3C lsb msb len (little-endian address per shickenchit)
    assert s.transport.sent[-1] == bytes.fromhex("3C002004")
    with pytest.raises(gs.GemsSecureError):
        s.read_memory(0x10000, 1)   # address out of range


def test_dump_memory_concatenates_chunks():
    s = gs.GemsSecureSession(FakeSecureEcu())
    s.connect()
    assert s.unlock()
    assert s.dump_memory(0x1800, 0x30, chunk=0x10) == b"\xAA" * 0x30


def test_write_cid_framing_and_gate():
    s = gs.GemsSecureSession(FakeSecureEcu())
    s.connect()
    with pytest.raises(gs.GemsSecureLocked):
        s.write_cid(gs.CID_CONFIG, b"\x01")
    assert s.unlock()
    resp = s.write_cid(gs.CID_CONFIG, b"\x01")
    assert s.transport.sent[-1] == b"\x2E\x04\xBF\x01"
    assert resp[:1] == b"\x6E"


def test_backend_secure_session_requires_real_transport():
    from gems_t4.app.backend import Backend
    from gems_t4.transport.base import TransportError

    # no transport factory (virtual ECU) -> refused
    with pytest.raises(TransportError):
        Backend().secure_session()

    # with a real transport factory -> builds a session that can unlock
    b = Backend(transport_factory=lambda: FakeSecureEcu())
    s = b.secure_session()
    s.connect()
    assert s.unlock() is True
    s.close()
