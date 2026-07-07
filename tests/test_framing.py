"""Framing round-trips and error handling."""
from __future__ import annotations

import pytest

from gems_t4.protocol import framing
from gems_t4.protocol.messages import Request, Response


def test_request_round_trip():
    req = Request(0x21, b"\x01\x02")
    frame = framing.encode_request(req)
    target, source, data = framing.parse_frame(frame)
    assert target == framing.DEFAULT_ECU_ADDRESS
    assert source == framing.TESTER_ADDRESS
    assert data == b"\x21\x01\x02"
    assert framing.decode_request(frame) == req


def test_positive_response_round_trip():
    resp = Response.positive(0x21, b"\x05\xAA")
    frame = framing.encode_response(resp)
    decoded = framing.decode_response(frame, request_service=0x21)
    assert not decoded.is_negative
    assert decoded.service == 0x21
    assert decoded.data == b"\x05\xAA"


def test_negative_response_round_trip():
    resp = Response.negative(0x21, 0x31)
    frame = framing.encode_response(resp)
    decoded = framing.decode_response(frame, request_service=0x21)
    assert decoded.is_negative
    assert decoded.nrc == 0x31
    assert decoded.service == 0x21


def test_checksum_detects_corruption():
    frame = bytearray(framing.encode_request(Request(0x3E)))
    frame[-1] ^= 0xFF  # corrupt checksum
    with pytest.raises(framing.ChecksumError):
        framing.parse_frame(bytes(frame))


def test_length_mismatch_rejected():
    frame = framing.encode_request(Request(0x21, b"\x01"))
    with pytest.raises(framing.FramingError):
        framing.parse_frame(frame[:-1])  # drop a byte


def test_checksum_is_sum_mod_256():
    assert framing.checksum(b"\x80\x10\xF1\x01\x3E") == (0x80 + 0x10 + 0xF1 + 0x01 + 0x3E) & 0xFF
