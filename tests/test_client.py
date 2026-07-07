"""KwpClient exercised over a fake transport (no hardware, no virtual ECU)."""
from __future__ import annotations

import pytest

from gems_t4.protocol import framing
from gems_t4.protocol.client import KwpClient, ProtocolError
from gems_t4.protocol.messages import NegativeResponse, Request, Response
from gems_t4.protocol.security import compute_key
from gems_t4.transport.base import InitResult, Transport


class FakeTransport(Transport):
    """A transport that answers each request via a responder callback."""

    def __init__(self, responder):
        self._responder = responder
        self._open = False
        self._pending: bytes | None = None

    def open(self):
        self._open = True

    def close(self):
        self._open = False

    def is_open(self):
        return self._open

    def init(self, address, mode="slow"):
        return InitResult()

    def send(self, frame):
        req = framing.decode_request(frame)
        resp = self._responder(req)
        self._pending = framing.encode_response(resp)

    def receive(self, timeout=None):
        assert self._pending is not None
        frame, self._pending = self._pending, None
        return frame


def test_read_data_by_local_id_returns_value_bytes():
    def responder(req: Request) -> Response:
        assert req.service == 0x21
        return Response.positive(0x21, bytes([req.data[0], 0xAA, 0xBB]))

    client = KwpClient(FakeTransport(responder))
    client.connect()
    assert client.read_data_by_local_id(0x05) == b"\xAA\xBB"


def test_read_data_by_local_id_mismatched_echo_raises():
    def responder(req: Request) -> Response:
        return Response.positive(0x21, bytes([0x99, 0x00]))  # wrong echo

    client = KwpClient(FakeTransport(responder))
    client.connect()
    with pytest.raises(ProtocolError):
        client.read_data_by_local_id(0x05)


def test_expect_positive_raises_on_negative():
    def responder(req: Request) -> Response:
        return Response.negative(req.service, 0x11)

    client = KwpClient(FakeTransport(responder))
    client.connect()
    with pytest.raises(NegativeResponse):
        client.start_session()


def test_security_access_round_trips_with_compute_key():
    seed = 0x1234
    state = {"expected": compute_key(seed)}

    def responder(req: Request) -> Response:
        if req.data and req.data[0] == 0x01:
            return Response.positive(0x27, bytes([0x01, seed >> 8, seed & 0xFF]))
        key = (req.data[1] << 8) | req.data[2]
        if key == state["expected"]:
            return Response.positive(0x27, bytes([0x02]))
        return Response.negative(0x27, 0x35)

    client = KwpClient(FakeTransport(responder))
    client.connect()
    client.security_access(compute_key)  # should not raise


def test_actuator_returns_negative_without_raising():
    def responder(req: Request) -> Response:
        return Response.negative(0x30, 0x22)

    client = KwpClient(FakeTransport(responder))
    client.connect()
    resp = client.actuator(0x03, 1)
    assert resp.is_negative and resp.nrc == 0x22
