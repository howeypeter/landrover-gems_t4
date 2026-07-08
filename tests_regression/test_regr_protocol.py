"""Independent regression tests for the protocol layer.

Derived from INTERFACES.md (the frozen build contract), firmware/HOST_PROTOCOL.md,
and the module docstrings — NOT from the existing tests/ suite.

Covers: framing round-trips + checksum + malformed-frame rejection, init.py
pure-data contract, security.py seed->key, TimingPolicy, and KwpClient behavior
against a scripted in-memory Transport.
"""
from __future__ import annotations

import pathlib

import pytest

from gems_t4.protocol import framing, init, security
from gems_t4.protocol.client import KwpClient, ProtocolError
from gems_t4.protocol.messages import NRC, NegativeResponse, Request, Response
from gems_t4.protocol.timing import TimingPolicy
from gems_t4.transport.base import InitResult, Transport, TransportTimeout

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# framing: checksum + frame build/parse
# --------------------------------------------------------------------------- #
class TestChecksum:
    def test_checksum_is_sum_mod_256(self):
        # INTERFACES.md: "CS = 8-bit sum of every preceding byte in the frame, mod 256"
        assert framing.checksum(b"\x01\x02\x03") == 6
        assert framing.checksum(b"\xff\x01") == 0  # wraps mod 256
        assert framing.checksum(b"") == 0
        assert framing.checksum(bytes([0x80, 0x10, 0xF1, 0x01, 0x3E])) == 0xC0

    def test_build_frame_layout(self):
        # [FMT=0x80][TGT][SRC][LEN][data...][CS] per INTERFACES.md wire format.
        frame = framing.build_frame(b"\x3e", target=0x10, source=0xF1)
        assert frame == bytes([0x80, 0x10, 0xF1, 0x01, 0x3E, 0xC0])

    def test_parse_frame_round_trip(self):
        data = bytes(range(1, 40))
        frame = framing.build_frame(data, target=0x10, source=0xF1)
        target, source, parsed = framing.parse_frame(frame)
        assert (target, source, parsed) == (0x10, 0xF1, data)

    def test_build_frame_rejects_bad_lengths_and_addresses(self):
        with pytest.raises(framing.FramingError):
            framing.build_frame(b"", target=0x10, source=0xF1)  # LEN is 1..255
        with pytest.raises(framing.FramingError):
            framing.build_frame(bytes(256), target=0x10, source=0xF1)
        # 255 data bytes is the documented maximum and must work.
        frame = framing.build_frame(bytes(255), target=0x10, source=0xF1)
        assert framing.parse_frame(frame)[2] == bytes(255)
        with pytest.raises(framing.FramingError):
            framing.build_frame(b"\x3e", target=0x100, source=0xF1)
        with pytest.raises(framing.FramingError):
            framing.build_frame(b"\x3e", target=0x10, source=-1)

    def test_parse_frame_rejects_malformed(self):
        good = framing.build_frame(b"\x3e", target=0x10, source=0xF1)
        # Too short.
        with pytest.raises(framing.FramingError):
            framing.parse_frame(good[:5])
        # Wrong format byte.
        bad_fmt = bytes([0x81]) + good[1:]
        with pytest.raises(framing.FramingError):
            framing.parse_frame(bad_fmt)
        # Length field disagrees with actual data length.
        bad_len = bytearray(good)
        bad_len[3] = 2
        with pytest.raises(framing.FramingError):
            framing.parse_frame(bytes(bad_len))

    def test_parse_frame_rejects_bad_checksum(self):
        good = bytearray(framing.build_frame(b"\x3e", target=0x10, source=0xF1))
        good[-1] ^= 0xFF
        with pytest.raises(framing.ChecksumError):
            framing.parse_frame(bytes(good))
        # ChecksumError must be a FramingError subclass so one except catches both.
        assert issubclass(framing.ChecksumError, framing.FramingError)


class TestRequestResponseCodecs:
    def test_encode_request_decode_request_round_trip(self):
        req = Request(0x21, b"\x05")
        frame = framing.encode_request(req)
        # Tester->ECU: target is the ECU (0x10), source is the tester (0xF1).
        target, source, data = framing.parse_frame(frame)
        assert (target, source) == (framing.DEFAULT_ECU_ADDRESS, framing.TESTER_ADDRESS)
        assert data == b"\x21\x05"
        back = framing.decode_request(frame)
        assert back.service == 0x21
        assert back.data == b"\x05"

    def test_positive_response_round_trip_and_sid_offset(self):
        resp = Response.positive(0x21, b"\x05\x12\x34")
        frame = framing.encode_response(resp)
        target, source, data = framing.parse_frame(frame)
        # ECU->tester: addresses swapped relative to the request.
        assert (target, source) == (framing.TESTER_ADDRESS, framing.DEFAULT_ECU_ADDRESS)
        assert data[0] == 0x61  # SID + 0x40 on the wire
        decoded = framing.decode_response(frame, request_service=0x21)
        assert not decoded.is_negative
        assert decoded.service == 0x21  # labelled with the REQUEST sid
        assert decoded.data == b"\x05\x12\x34"

    def test_negative_response_round_trip(self):
        # Negative form on the wire: [0x7F][request SID][NRC].
        resp = Response.negative(0x30, NRC.CONDITIONS_NOT_CORRECT)
        frame = framing.encode_response(resp)
        _, _, data = framing.parse_frame(frame)
        assert data == bytes([0x7F, 0x30, 0x22])
        decoded = framing.decode_response(frame, request_service=0x30)
        assert decoded.is_negative
        assert decoded.service == 0x30
        assert decoded.nrc == NRC.CONDITIONS_NOT_CORRECT

    def test_decode_response_rejects_wrong_positive_sid(self):
        # A positive response whose SID is not request+0x40 must be rejected.
        resp = Response.positive(0x21, b"\x05")
        frame = framing.encode_response(resp)
        with pytest.raises(framing.FramingError):
            framing.decode_response(frame, request_service=0x18)

    def test_decode_response_rejects_malformed_negative(self):
        # Negative response must be exactly 3 service bytes.
        frame = framing.build_frame(
            bytes([0x7F, 0x21, 0x31, 0x00]),
            target=framing.TESTER_ADDRESS,
            source=framing.DEFAULT_ECU_ADDRESS,
        )
        with pytest.raises(framing.FramingError):
            framing.decode_response(frame, request_service=0x21)

    def test_custom_addresses_honoured(self):
        req = Request(0x3E)
        frame = framing.encode_request(req, ecu_address=0x74, tester_address=0xF0)
        target, source, _ = framing.parse_frame(frame)
        assert (target, source) == (0x74, 0xF0)


# --------------------------------------------------------------------------- #
# init.py — pure data contract
# --------------------------------------------------------------------------- #
class TestInitConstants:
    def test_documented_constants(self):
        assert init.GENERIC_INIT_ADDRESS == 0x33
        assert init.ROVER_INIT_ADDRESS == 0x16
        assert init.SYNC_BYTE == 0x55
        assert init.DEFAULT_KEYBYTES == b"\x08\x08"

    def test_normalize_mode(self):
        assert init.normalize_mode("slow") is init.InitMode.SLOW
        assert init.normalize_mode("fast") is init.InitMode.FAST
        assert init.normalize_mode("FAST") is init.InitMode.FAST  # case-insensitive
        assert init.normalize_mode(init.InitMode.SLOW) is init.InitMode.SLOW
        with pytest.raises(ValueError):
            init.normalize_mode("medium")

    def test_invert_byte(self):
        assert init.invert_byte(0x33) == 0xCC
        assert init.invert_byte(0x00) == 0xFF
        assert init.invert_byte(0xFF) == 0x00
        for v in (0x16, 0x55, 0x08):
            assert init.invert_byte(init.invert_byte(v)) == v  # involution
            assert 0 <= init.invert_byte(v) <= 0xFF


# --------------------------------------------------------------------------- #
# security.py — seed -> key
# --------------------------------------------------------------------------- #
class TestSecurity:
    def test_compute_key_is_deterministic_16_bit(self):
        assert security.SEED_SIZE == 16
        for seed in (0x0000, 0x0001, 0x1234, 0xBEEF, 0xFFFF):
            key = security.compute_key(seed)
            assert key == security.compute_key(seed)  # deterministic
            assert 0 <= key <= 0xFFFF

    def test_compute_key_masks_seed_to_16_bits(self):
        assert security.compute_key(0x1BEEF) == security.compute_key(0xBEEF)

    def test_compute_key_rejects_negative_seed(self):
        with pytest.raises(ValueError):
            security.compute_key(-1)

    def test_compute_key_not_identity(self):
        # A toy transform, but it must actually transform (client/ECU agreement
        # would be vacuous if key == seed for everything).
        assert any(security.compute_key(s) != s for s in range(0, 0x100))


# --------------------------------------------------------------------------- #
# timing.py — TimingPolicy
# --------------------------------------------------------------------------- #
class TestTimingPolicy:
    def test_defaults_are_sane_kwp_values(self):
        t = TimingPolicy()
        assert t.response_timeout > 0
        for window in (t.p1, t.p2, t.p3, t.p4):
            assert 0 < window < 1.0  # sub-second inter-byte/turnaround windows

    def test_as_milliseconds_matches_set_timing_encoding(self):
        t = TimingPolicy(p1=0.020, p2=0.050, p3=0.055, p4=0.020)
        ms = t.as_milliseconds()
        assert ms == (20, 50, 55, 20)
        assert all(isinstance(v, int) for v in ms)

    def test_policy_is_frozen(self):
        t = TimingPolicy()
        with pytest.raises(Exception):
            t.p1 = 0.5  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# KwpClient — against a scripted in-memory Transport (no hardware)
# --------------------------------------------------------------------------- #
class ScriptedTransport(Transport):
    """Minimal Transport: decodes request frames, answers via a handler fn."""

    def __init__(self, handler=None):
        self.handler = handler or (lambda req: Response.positive(req.service))
        self.opened = False
        self.closed = False
        self.init_calls: list[tuple[int, str]] = []
        self.receive_timeouts: list[float | None] = []
        self.seen_requests: list[Request] = []
        self._pending: bytes | None = None

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.closed = True

    def is_open(self) -> bool:
        return self.opened and not self.closed

    def init(self, address: int, mode: str = "slow") -> InitResult:
        self.init_calls.append((address, mode))
        return InitResult(keybytes=b"\x6b\x8f")

    def send(self, frame: bytes) -> None:
        req = framing.decode_request(frame)
        self.seen_requests.append(req)
        self._pending = framing.encode_response(self.handler(req))

    def receive(self, timeout: float | None = None) -> bytes:
        self.receive_timeouts.append(timeout)
        if self._pending is None:
            raise TransportTimeout("nothing pending")
        frame, self._pending = self._pending, None
        return frame


class TestKwpClientLifecycle:
    def test_connect_opens_and_inits_and_returns_initresult(self):
        t = ScriptedTransport()
        client = KwpClient(t)
        result = client.connect()
        assert t.opened
        assert isinstance(result, InitResult)
        assert result.keybytes == b"\x6b\x8f"
        # Default ECU address 0x10 and default "slow" mode per INTERFACES.md.
        assert t.init_calls == [(0x10, "slow")]

    def test_connect_uses_configured_address_and_mode(self):
        t = ScriptedTransport()
        client = KwpClient(t, ecu_address=0x74, tester_address=0xF0)
        client.connect(mode="fast")
        assert t.init_calls == [(0x74, "fast")]

    def test_close_closes_transport(self):
        t = ScriptedTransport()
        client = KwpClient(t)
        client.connect()
        client.close()
        assert t.closed


class TestKwpClientRequests:
    def test_request_happy_path(self):
        t = ScriptedTransport(lambda req: Response.positive(req.service, b"\xab\xcd"))
        client = KwpClient(t)
        client.connect()
        resp = client.request(Request(0x1A, b"\x80"))
        assert not resp.is_negative
        assert resp.service == 0x1A
        assert resp.data == b"\xab\xcd"
        assert t.seen_requests[-1] == Request(0x1A, b"\x80")

    def test_default_and_explicit_timeouts_passed_to_receive(self):
        t = ScriptedTransport()
        client = KwpClient(t, timing=TimingPolicy(response_timeout=1.5))
        client.connect()
        client.request(Request(0x3E))
        assert t.receive_timeouts[-1] == 1.5
        client.request(Request(0x3E), timeout=0.25)
        assert t.receive_timeouts[-1] == 0.25

    def test_negative_response_returned_raw_and_raised_when_expected(self):
        t = ScriptedTransport(
            lambda req: Response.negative(req.service, NRC.SERVICE_NOT_SUPPORTED)
        )
        client = KwpClient(t)
        client.connect()
        resp = client.request(Request(0x18))
        assert resp.is_negative and resp.nrc == NRC.SERVICE_NOT_SUPPORTED
        with pytest.raises(NegativeResponse) as exc:
            client.request(Request(0x18), expect_positive=True)
        assert exc.value.nrc == NRC.SERVICE_NOT_SUPPORTED
        assert exc.value.service == 0x18

    def test_start_session_and_tester_present_wire_shape(self):
        def handler(req: Request) -> Response:
            if req.service == 0x10:
                return Response.positive(0x10, req.data)  # echo session byte
            return Response.positive(req.service)

        t = ScriptedTransport(handler)
        client = KwpClient(t)
        client.connect()
        resp = client.start_session()
        assert t.seen_requests[-1] == Request(0x10, b"\x81")  # default session 0x81
        assert resp.data == b"\x81"
        client.start_session(0x85)
        assert t.seen_requests[-1] == Request(0x10, b"\x85")
        client.tester_present()
        assert t.seen_requests[-1] == Request(0x3E, b"")  # empty payload

    def test_read_data_by_local_id_returns_value_bytes(self):
        t = ScriptedTransport(
            lambda req: Response.positive(0x21, bytes([req.data[0], 0x12, 0x34]))
        )
        client = KwpClient(t)
        client.connect()
        assert client.read_data_by_local_id(0x05) == b"\x12\x34"
        assert t.seen_requests[-1] == Request(0x21, b"\x05")

    def test_read_data_by_local_id_mismatched_echo_raises_protocolerror(self):
        t = ScriptedTransport(lambda req: Response.positive(0x21, b"\x99\x00"))
        client = KwpClient(t)
        client.connect()
        with pytest.raises(ProtocolError):
            client.read_data_by_local_id(0x05)

    def test_read_data_by_local_id_negative_raises(self):
        t = ScriptedTransport(
            lambda req: Response.negative(0x21, NRC.REQUEST_OUT_OF_RANGE)
        )
        client = KwpClient(t)
        client.connect()
        with pytest.raises(NegativeResponse):
            client.read_data_by_local_id(0x05)

    def test_dtc_and_write_and_actuator_wrappers(self):
        def handler(req: Request) -> Response:
            if req.service == 0x18:
                return Response.positive(0x18, b"\x01\x01\x18\xe0")
            if req.service == 0x3B:
                return Response.positive(0x3B, bytes([req.data[0]]))
            if req.service == 0x30:
                return Response.negative(0x30, NRC.CONDITIONS_NOT_CORRECT)
            return Response.positive(req.service)

        t = ScriptedTransport(handler)
        client = KwpClient(t)
        client.connect()
        assert client.read_dtcs_raw() == b"\x01\x01\x18\xe0"
        assert not client.clear_dtcs().is_negative
        assert t.seen_requests[-1] == Request(0x14, b"")
        client.write_data_by_local_id(0x02, b"AB")
        assert t.seen_requests[-1] == Request(0x3B, b"\x02AB")
        # Actuator refusals come back as a raw negative Response — no raise.
        resp = client.actuator(0x01, 0x01)
        assert resp.is_negative and resp.nrc == NRC.CONDITIONS_NOT_CORRECT
        assert t.seen_requests[-1] == Request(0x30, b"\x01\x01")


class TestKwpClientSecurityAccess:
    SEED = 0xBEEF

    def _ecu_handler(self, req: Request) -> Response:
        if req.service != 0x27:
            return Response.negative(req.service, NRC.SERVICE_NOT_SUPPORTED)
        if req.data[0] == 0x01:  # seed request -> [0x01][seed hi][seed lo]
            return Response.positive(
                0x27, bytes([0x01, self.SEED >> 8, self.SEED & 0xFF])
            )
        if req.data[0] == 0x02:  # key submit
            key = (req.data[1] << 8) | req.data[2]
            if key == security.compute_key(self.SEED):
                return Response.positive(0x27, b"\x02")
            return Response.negative(0x27, NRC.INVALID_KEY)
        return Response.negative(0x27, NRC.SUBFUNCTION_NOT_SUPPORTED)

    def test_security_access_round_trips_with_compute_key(self):
        t = ScriptedTransport(self._ecu_handler)
        client = KwpClient(t)
        client.connect()
        client.security_access(security.compute_key)  # must not raise
        # Two exchanges: 27 01 (seed) then 27 02 [key hi][key lo].
        assert [r.service for r in t.seen_requests] == [0x27, 0x27]
        assert t.seen_requests[0].data == b"\x01"
        assert t.seen_requests[1].data[0] == 0x02
        assert len(t.seen_requests[1].data) == 3

    def test_security_access_wrong_key_raises_invalid_key(self):
        t = ScriptedTransport(self._ecu_handler)
        client = KwpClient(t)
        client.connect()
        with pytest.raises(NegativeResponse) as exc:
            client.security_access(lambda seed: (seed + 1) & 0xFFFF)
        assert exc.value.nrc == NRC.INVALID_KEY


# --------------------------------------------------------------------------- #
# Layering purity — "No I/O or time.sleep in protocol/ or gems/" (INTERFACES.md)
# --------------------------------------------------------------------------- #
class TestLayeringPurity:
    @pytest.mark.parametrize("package", ["protocol", "gems"])
    def test_no_sleep_or_serial_in_pure_layers(self, package: str):
        pkg_dir = PROJECT_ROOT / "gems_t4" / package
        offenders: list[str] = []
        for path in sorted(pkg_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for needle in ("time.sleep(", "import serial", "from serial"):
                if needle in text:
                    offenders.append(f"{path.name}: {needle}")
        assert not offenders, (
            f"pure layer gems_t4/{package}/ must not sleep or touch serial I/O; "
            f"found: {offenders}"
        )
