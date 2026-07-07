"""KWP2000 / ISO-14230 frame encode/decode (the wire format).

A *frame* is the byte string a :class:`~gems_t4.transport.base.Transport`
carries end-to-end::

    [FMT=0x80] [TGT] [SRC] [LEN] [ data ... ] [CS]

* ``FMT`` is fixed at ``0x80`` (address bytes present, explicit length byte).
* ``TGT`` / ``SRC`` are the target / source addresses. The tester is
  :data:`TESTER_ADDRESS` (``0xF1``); the ECU is :data:`DEFAULT_ECU_ADDRESS`
  (``0x10``).
* ``LEN`` is the number of ``data`` bytes (1..255).
* ``data`` are the service bytes:

  * request       -> ``[SID][payload...]``
  * positive resp -> ``[SID + 0x40][payload...]``
  * negative resp -> ``[0x7F][SID][NRC]``
* ``CS`` is the 8-bit sum of *every* preceding byte in the frame, mod 256.

Four functions form two symmetric pairs that must round-trip:

* client side:  :func:`encode_request` / :func:`decode_response`
* ECU side:     :func:`decode_request` / :func:`encode_response`

This module is pure: no I/O, no sleeping, no GEMS knowledge.
"""
from __future__ import annotations

from gems_t4.protocol.messages import (
    NEGATIVE_RESPONSE_SID,
    POSITIVE_RESPONSE_OFFSET,
    Request,
    Response,
)

__all__ = [
    "FramingError",
    "ChecksumError",
    "TESTER_ADDRESS",
    "DEFAULT_ECU_ADDRESS",
    "FORMAT_BYTE",
    "checksum",
    "build_frame",
    "parse_frame",
    "encode_request",
    "decode_request",
    "encode_response",
    "decode_response",
]

#: Fixed format byte: address bytes present, explicit length byte follows.
FORMAT_BYTE = 0x80

#: Conventional tester (diagnostic client) address.
TESTER_ADDRESS = 0xF1

#: Conventional GEMS ECU address on the K-line.
DEFAULT_ECU_ADDRESS = 0x10


class FramingError(Exception):
    """A frame is malformed (too short, bad format byte, wrong length)."""


class ChecksumError(FramingError):
    """A frame's trailing checksum byte does not match the computed sum."""

    def __init__(self, expected: int, actual: int) -> None:
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"checksum mismatch: expected 0x{expected:02X}, got 0x{actual:02X}"
        )


def checksum(payload: bytes) -> int:
    """Return the KWP2000 checksum: the 8-bit sum of ``payload`` mod 256."""
    return sum(payload) & 0xFF


def build_frame(data: bytes, *, target: int, source: int) -> bytes:
    """Build a complete frame carrying ``data`` bytes.

    Parameters
    ----------
    data:
        The service bytes (``[SID][payload...]`` etc.), 1..255 bytes.
    target:
        Target address (goes in the ``TGT`` field).
    source:
        Source address (goes in the ``SRC`` field).

    Raises
    ------
    FramingError
        If ``data`` is empty or longer than 255 bytes, or if either address
        is out of the 0..255 range.
    """
    data = bytes(data)
    if not 1 <= len(data) <= 255:
        raise FramingError(f"data length out of range (1..255): {len(data)}")
    if not 0 <= target <= 0xFF:
        raise FramingError(f"target address out of range: {target}")
    if not 0 <= source <= 0xFF:
        raise FramingError(f"source address out of range: {source}")

    header = bytes([FORMAT_BYTE, target, source, len(data)])
    body = header + data
    return body + bytes([checksum(body)])


def parse_frame(frame: bytes) -> tuple[int, int, bytes]:
    """Parse a complete frame, validating length and checksum.

    Returns ``(target, source, data)``.

    Raises
    ------
    FramingError
        If the frame is too short, has the wrong format byte, or the length
        field disagrees with the actual number of data bytes.
    ChecksumError
        If the trailing checksum byte is wrong.
    """
    frame = bytes(frame)
    # Minimum: FMT TGT SRC LEN + at least one data byte + CS = 6 bytes.
    if len(frame) < 6:
        raise FramingError(f"frame too short: {len(frame)} bytes")
    if frame[0] != FORMAT_BYTE:
        raise FramingError(
            f"bad format byte: expected 0x{FORMAT_BYTE:02X}, got 0x{frame[0]:02X}"
        )

    target = frame[1]
    source = frame[2]
    length = frame[3]
    expected_total = 4 + length + 1  # header + data + checksum
    if len(frame) != expected_total:
        raise FramingError(
            f"length field ({length}) implies {expected_total}-byte frame, "
            f"got {len(frame)} bytes"
        )

    body = frame[:-1]
    expected_cs = checksum(body)
    actual_cs = frame[-1]
    if expected_cs != actual_cs:
        raise ChecksumError(expected_cs, actual_cs)

    data = frame[4 : 4 + length]
    return target, source, data


# --------------------------------------------------------------------------- #
# Client side: encode_request / decode_response
# --------------------------------------------------------------------------- #
def encode_request(
    req: Request,
    *,
    ecu_address: int = DEFAULT_ECU_ADDRESS,
    tester_address: int = TESTER_ADDRESS,
) -> bytes:
    """Encode a :class:`Request` into a wire frame (tester -> ECU)."""
    data = bytes([req.service, *req.data])
    return build_frame(data, target=ecu_address, source=tester_address)


def decode_response(frame: bytes, request_service: int) -> Response:
    """Decode a wire frame into a :class:`Response` (ECU -> tester).

    ``request_service`` is the SID of the request this answers; it lets us
    label the returned :class:`Response` with the *request* SID (not the
    echoed ``+0x40`` value) and sanity-check a positive echo.

    Raises
    ------
    FramingError / ChecksumError
        On a malformed frame.
    """
    _target, _source, data = parse_frame(frame)
    if not data:
        raise FramingError("response frame carries no service bytes")

    sid = data[0]
    if sid == NEGATIVE_RESPONSE_SID:
        # [0x7F][request SID][NRC]
        if len(data) != 3:
            raise FramingError(
                f"negative response must be 3 bytes, got {len(data)}"
            )
        echoed_sid = data[1]
        nrc = data[2]
        return Response.negative(echoed_sid, nrc)

    # Positive response: SID should be request_service + 0x40.
    expected_positive = (request_service + POSITIVE_RESPONSE_OFFSET) & 0xFF
    if sid != expected_positive:
        raise FramingError(
            f"positive response SID 0x{sid:02X} does not match expected "
            f"0x{expected_positive:02X} for request 0x{request_service:02X}"
        )
    return Response.positive(request_service, data[1:])


# --------------------------------------------------------------------------- #
# ECU side: decode_request / encode_response
# --------------------------------------------------------------------------- #
def decode_request(frame: bytes) -> Request:
    """Decode a wire frame into a :class:`Request` (used by the virtual ECU).

    Raises
    ------
    FramingError / ChecksumError
        On a malformed frame.
    """
    _target, _source, data = parse_frame(frame)
    if not data:
        raise FramingError("request frame carries no service bytes")
    return Request(service=data[0], data=data[1:])


def encode_response(
    resp: Response,
    *,
    ecu_address: int = DEFAULT_ECU_ADDRESS,
    tester_address: int = TESTER_ADDRESS,
) -> bytes:
    """Encode a :class:`Response` into a wire frame (ECU -> tester).

    Positive responses become ``[SID + 0x40][payload...]``; negative responses
    become ``[0x7F][request SID][NRC]``.
    """
    if resp.is_negative:
        nrc = resp.nrc if resp.nrc is not None else 0
        data = bytes([NEGATIVE_RESPONSE_SID, resp.service & 0xFF, nrc & 0xFF])
    else:
        positive_sid = (resp.service + POSITIVE_RESPONSE_OFFSET) & 0xFF
        data = bytes([positive_sid, *resp.data])
    # Note: TGT/SRC are swapped relative to a request (ECU answers the tester).
    return build_frame(data, target=tester_address, source=ecu_address)
