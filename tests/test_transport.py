"""Virtual transport round-trip and Pico host-protocol framing."""
from __future__ import annotations

from gems_t4.protocol import framing
from gems_t4.protocol.messages import Request, Response
from gems_t4.transport import pico
from gems_t4.transport.virtual import VirtualTransport


class _CannedEcu:
    def handle(self, request: Request) -> Response:
        return Response.positive(request.service, b"\xDE\xAD")

    def tick(self, dt: float) -> None:
        pass


def test_virtual_transport_round_trips_a_request():
    t = VirtualTransport(_CannedEcu())
    t.open()
    t.send(framing.encode_request(Request(0x21, b"\x01")))
    resp = framing.decode_response(t.receive(), request_service=0x21)
    assert resp.data == b"\xDE\xAD"


def test_pico_host_frame_round_trip():
    frame = pico.encode_host(pico.CMD_SEND_RECV, b"\x01\x02\x03")
    assert frame[0] == pico.HOST_START
    # reconstruct a pico response and decode it
    body = bytes([pico.STATUS_OK, 3]) + b"\x01\x02\x03"
    resp = bytes([pico.PICO_START]) + body + bytes([pico.crc8(body)])
    status, payload = pico.decode_pico(resp)
    assert status == pico.STATUS_OK
    assert payload == b"\x01\x02\x03"


class _FakeSerial:
    """Loopback serial: echoes the KWP frame in a SEND_RECV, canned INIT/PING."""

    def __init__(self):
        self._in = bytearray()

    def write(self, data: bytes):
        cmd, length = data[1], data[2]
        payload = bytes(data[3 : 3 + length])
        if cmd == pico.CMD_PING:
            out = b"PICO v1"
        elif cmd == pico.CMD_INIT:
            out = b"\x08\x08"
        else:  # SEND_RECV echoes
            out = payload
        body = bytes([pico.STATUS_OK, len(out)]) + out
        self._in += bytes([pico.PICO_START]) + body + bytes([pico.crc8(body)])

    def read(self, n: int) -> bytes:
        chunk = bytes(self._in[:n])
        del self._in[:n]
        return chunk


def test_pico_transport_over_fake_serial():
    t = pico.PicoAdapterTransport(serial_obj=_FakeSerial())
    t.open()
    assert t.ping() == b"PICO v1"
    assert t.init(0x10, "slow").keybytes == b"\x08\x08"
    sent = framing.encode_request(Request(0x3E))
    t.send(sent)
    assert t.receive() == sent  # loopback echo
