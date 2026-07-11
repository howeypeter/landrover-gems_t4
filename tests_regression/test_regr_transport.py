"""Independent regression tests for the transport layer.

Derived from INTERFACES.md, firmware/HOST_PROTOCOL.md, and module docstrings —
NOT from the existing tests/ suite.

Covers: VirtualTransport (init result, request/response via an EcuHandler,
latency hook structure, closed-transport errors), PicoAdapterTransport against
an in-memory fake serial (host-protocol framing per HOST_PROTOCOL.md, INIT
encoding, status/error mapping), and the FtdiKlineTransport documented stub.
"""
from __future__ import annotations

import pytest

from gems_t4.protocol import framing
from gems_t4.protocol.client import KwpClient
from gems_t4.protocol.messages import Request, Response
from gems_t4.transport.base import (
    InitError,
    InitResult,
    TransportClosed,
    TransportError,
    TransportTimeout,
)
from gems_t4.transport.ftdi import FtdiKlineTransport
from gems_t4.transport.pico import PicoAdapterTransport
from gems_t4.transport.virtual import VirtualTransport


# --------------------------------------------------------------------------- #
# VirtualTransport
# --------------------------------------------------------------------------- #
class EchoEcu:
    """Tiny EcuHandler: answers every request positively, echoing its data."""

    def __init__(self):
        self.requests: list[Request] = []

    def handle(self, request: Request) -> Response:
        self.requests.append(request)
        return Response.positive(request.service, request.data)

    def tick(self, dt: float) -> None:  # pragma: no cover - structural no-op
        pass


class TestVirtualTransport:
    def test_init_returns_canned_initresult_and_opens(self):
        vt = VirtualTransport(EchoEcu())
        assert not vt.is_open()
        result = vt.init(0x10, "slow")
        # Init must succeed even before open() and return the defaults.
        assert vt.is_open()
        assert isinstance(result, InitResult)
        assert result.keybytes == b"\x08\x08"
        assert result.baud == 10400
        assert result.protocol == "KWP2000"

    def test_send_receive_round_trip_and_address_swap(self):
        ecu = EchoEcu()
        vt = VirtualTransport(ecu)
        vt.open()
        req_frame = framing.encode_request(Request(0x21, b"\x05"))
        vt.send(req_frame)
        assert ecu.requests == [Request(0x21, b"\x05")]
        resp_frame = vt.receive()
        target, source, data = framing.parse_frame(resp_frame)
        # Response frame flows ECU -> tester: addresses are swapped.
        assert (target, source) == (framing.TESTER_ADDRESS, framing.DEFAULT_ECU_ADDRESS)
        assert data == b"\x61\x05"  # SID+0x40, echoed payload

    def test_receive_without_pending_response_times_out(self):
        vt = VirtualTransport(EchoEcu())
        vt.open()
        with pytest.raises(TransportTimeout):
            vt.receive()
        vt.send(framing.encode_request(Request(0x3E)))
        vt.receive()
        # The buffer is single-shot: a second receive has nothing to read.
        with pytest.raises(TransportTimeout):
            vt.receive()

    def test_closed_transport_raises_transportclosed(self):
        vt = VirtualTransport(EchoEcu())
        with pytest.raises(TransportClosed):
            vt.send(framing.encode_request(Request(0x3E)))
        with pytest.raises(TransportClosed):
            vt.receive()
        # close() must be idempotent (Transport base contract).
        vt.close()
        vt.close()
        # Closing drops any pending response.
        vt.open()
        vt.send(framing.encode_request(Request(0x3E)))
        vt.close()
        vt.open()
        with pytest.raises(TransportTimeout):
            vt.receive()

    def test_negative_latency_rejected(self):
        with pytest.raises(ValueError):
            VirtualTransport(EchoEcu(), latency=-0.1)

    def test_latency_hook_structure(self, monkeypatch):
        # Structural check only: latency>0 routes through time.sleep with the
        # configured value; the default latency=0.0 never touches the clock.
        calls: list[float] = []
        monkeypatch.setattr(
            "gems_t4.transport.virtual.time.sleep", lambda s: calls.append(s)
        )
        slow = VirtualTransport(EchoEcu(), latency=0.05)
        slow.open()
        slow.send(framing.encode_request(Request(0x3E)))
        slow.receive()
        assert calls == [0.05]

        calls.clear()
        instant = VirtualTransport(EchoEcu())  # default latency = 0.0
        instant.open()
        instant.send(framing.encode_request(Request(0x3E)))
        instant.receive()
        assert calls == []

    def test_full_stack_against_real_virtual_ecu(self):
        # VirtualTransport wrapping the actual VirtualEcu, driven by KwpClient.
        from gems_t4.gems.virtual_ecu import VirtualEcu

        client = KwpClient(VirtualTransport(VirtualEcu()))
        result = client.connect()
        assert isinstance(result, InitResult)
        client.tester_present()  # positive 0x3E round trip, raises on failure
        # Unsupported SID must come back as a negative response
        # (SERVICE_NOT_SUPPORTED or REQUEST_OUT_OF_RANGE per INTERFACES.md).
        resp = client.request(Request(0xAA))
        assert resp.is_negative
        assert resp.nrc in (0x11, 0x31)
        client.close()


# --------------------------------------------------------------------------- #
# Pico host protocol helpers (built from firmware/HOST_PROTOCOL.md, not pico.py)
# --------------------------------------------------------------------------- #
def _xor8(body: bytes) -> int:
    c = 0
    for b in body:
        c ^= b
    return c


def host_frame(cmd: int, payload: bytes = b"") -> bytes:
    """Expected Host->Pico frame per HOST_PROTOCOL.md: A5 cmd len payload crc8."""
    body = bytes([cmd, len(payload)]) + payload
    return b"\xa5" + body + bytes([_xor8(body)])


def pico_frame(status: int, payload: bytes = b"") -> bytes:
    """Pico->Host frame per HOST_PROTOCOL.md: 5A status len payload crc8."""
    body = bytes([status, len(payload)]) + payload
    return b"\x5a" + body + bytes([_xor8(body)])


class FakeSerial:
    """In-memory stand-in for pyserial's Serial: write() records, read() drains."""

    def __init__(self, rx: bytes = b""):
        self.rx = bytearray(rx)
        self.written = bytearray()
        self.closed = False

    def write(self, data: bytes) -> int:
        self.written.extend(data)
        return len(data)

    def read(self, n: int = 1) -> bytes:
        out = bytes(self.rx[:n])
        del self.rx[:n]
        return out

    def close(self) -> None:
        self.closed = True


# A valid KWP TesterPresent frame (checksum = sum mod 256 per INTERFACES.md).
KWP_TESTER_PRESENT = bytes([0x80, 0x10, 0xF1, 0x01, 0x3E, 0xC0])
KWP_TP_RESPONSE = bytes([0x80, 0xF1, 0x10, 0x01, 0x7E, 0x00])


class TestPicoHostFraming:
    def test_encode_host_matches_documented_framing(self):
        from gems_t4.transport import pico

        assert pico.encode_host(pico.CMD_PING) == host_frame(0x01)
        assert pico.encode_host(pico.CMD_SEND_RECV, KWP_TESTER_PRESENT) == host_frame(
            0x03, KWP_TESTER_PRESENT
        )
        # crc8 = XOR of cmd, len, and all payload bytes (HOST_PROTOCOL.md).
        frame = pico.encode_host(0x02, b"\x33\x01")
        assert frame[-1] == 0x02 ^ 0x02 ^ 0x33 ^ 0x01

    def test_encode_host_rejects_oversize_payload(self):
        from gems_t4.transport.pico import encode_host

        with pytest.raises(ValueError):
            encode_host(0x03, bytes(256))

    def test_decode_pico_happy_and_malformed(self):
        from gems_t4.transport.pico import decode_pico

        assert decode_pico(pico_frame(0x00, b"PICO v1")) == (0x00, b"PICO v1")
        with pytest.raises(TransportError):
            decode_pico(b"\xa5" + pico_frame(0x00)[1:])  # wrong start byte
        with pytest.raises(TransportError):
            decode_pico(pico_frame(0x00, b"abc")[:-2])  # truncated payload
        corrupt = bytearray(pico_frame(0x00, b"abc"))
        corrupt[-1] ^= 0xFF
        with pytest.raises(TransportError):
            decode_pico(bytes(corrupt))  # crc mismatch


class TestPicoAdapterTransport:
    def test_ping_writes_ping_command_and_returns_version(self):
        fake = FakeSerial(pico_frame(0x00, b"PICO v1"))
        t = PicoAdapterTransport(serial_obj=fake)
        assert t.is_open()  # injected serial counts as open
        assert t.ping() == b"PICO v1"
        assert bytes(fake.written) == host_frame(0x01)

    def test_init_encodes_address_and_mode(self):
        fake = FakeSerial(pico_frame(0x00, b"\x08\x08"))
        t = PicoAdapterTransport(serial_obj=fake)
        result = t.init(0x33, "fast")
        # INIT (0x02) payload = [address][mode 0=slow/1=fast] per HOST_PROTOCOL.md.
        assert bytes(fake.written) == host_frame(0x02, b"\x33\x01")
        assert result.keybytes == b"\x08\x08"

        fake2 = FakeSerial(pico_frame(0x00, b"\x08\x08"))
        t2 = PicoAdapterTransport(serial_obj=fake2)
        t2.init(0x16, "slow")
        assert bytes(fake2.written) == host_frame(0x02, b"\x16\x00")

    def test_init_unknown_mode_and_failure_status(self):
        t = PicoAdapterTransport(serial_obj=FakeSerial())
        with pytest.raises(ValueError):
            t.init(0x33, "medium")
        t_fail = PicoAdapterTransport(
            serial_obj=FakeSerial(pico_frame(0x02))  # BUS_ERROR
        )
        with pytest.raises(InitError):
            t_fail.init(0x33, "slow")

    def test_send_recv_round_trip(self):
        fake = FakeSerial(pico_frame(0x00, KWP_TP_RESPONSE))
        t = PicoAdapterTransport(serial_obj=fake)
        t.send(KWP_TESTER_PRESENT)
        # SEND_RECV (0x03), payload = the complete KWP frame, length-prefixed.
        assert bytes(fake.written) == host_frame(0x03, KWP_TESTER_PRESENT)
        assert t.receive() == KWP_TP_RESPONSE
        # Buffered response is single-shot.
        with pytest.raises(TransportTimeout):
            t.receive()

    def test_status_timeout_maps_to_transporttimeout(self):
        # HOST_PROTOCOL.md: a SEND_RECV whose K-line reply never starts returns
        # TIMEOUT; "the Python side maps that to TransportTimeout".
        t = PicoAdapterTransport(serial_obj=FakeSerial(pico_frame(0x01)))
        with pytest.raises(TransportTimeout):
            t.send(KWP_TESTER_PRESENT)

    def test_status_bus_error_maps_to_transporterror(self):
        t = PicoAdapterTransport(serial_obj=FakeSerial(pico_frame(0x02)))
        with pytest.raises(TransportError) as exc:
            t.send(KWP_TESTER_PRESENT)
        assert not isinstance(exc.value, TransportTimeout)

    def test_silent_or_garbled_adapter(self):
        # No bytes at all -> timeout.
        with pytest.raises(TransportTimeout):
            PicoAdapterTransport(serial_obj=FakeSerial()).ping()
        # Wrong start byte -> transport error.
        with pytest.raises(TransportError):
            PicoAdapterTransport(serial_obj=FakeSerial(b"\xff" * 8)).ping()
        # Corrupted CRC from the Pico -> transport error.
        corrupt = bytearray(pico_frame(0x00, b"PICO v1"))
        corrupt[-1] ^= 0x01
        with pytest.raises(TransportError):
            PicoAdapterTransport(serial_obj=FakeSerial(bytes(corrupt))).ping()

    def test_closed_transport_raises(self):
        t = PicoAdapterTransport(serial_obj=FakeSerial())
        t.close()
        assert not t.is_open()
        with pytest.raises(TransportClosed):
            t.send(KWP_TESTER_PRESENT)
        with pytest.raises(TransportClosed):
            t.ping()
        t.close()  # idempotent


# --------------------------------------------------------------------------- #
# FTDI stub
# --------------------------------------------------------------------------- #
class TestFtdiStub:
    def test_documented_stub_raises_notimplemented(self):
        t = FtdiKlineTransport("COM3")
        assert not t.is_open()
        with pytest.raises(NotImplementedError):
            t.open()
        with pytest.raises(NotImplementedError):
            t.init(0x33)
        with pytest.raises(NotImplementedError):
            t.send(KWP_TESTER_PRESENT)
        with pytest.raises(NotImplementedError):
            t.receive()
        t.close()  # close must remain safe on the stub
        assert not t.is_open()
