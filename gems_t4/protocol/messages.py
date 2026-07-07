"""Core request/response value objects for the KWP2000-style service layer.

Transport- and framing-agnostic: a :class:`Request` is *what* the tester asks
the ECU; a :class:`Response` is *what* the ECU answers. Encoding these into
on-the-wire KWP2000/ISO-14230 frames (header, length, checksum) is the job of
:mod:`gems_t4.protocol.framing`; moving frame bytes across the K-line (or the
virtual ECU) is the job of :mod:`gems_t4.transport`.

Conventions
-----------
* A positive response to request service ``SID`` carries the SID echoed as
  ``SID + 0x40`` on the wire (e.g. request ``0x21`` -> positive ``0x61``).
* A negative response is the 3-byte form ``7F <SID> <NRC>``.
"""
from __future__ import annotations

from dataclasses import dataclass

#: SID that marks a negative response frame (``7F <request-sid> <nrc>``).
NEGATIVE_RESPONSE_SID = 0x7F

#: Offset added to a request SID to form the positive-response SID.
POSITIVE_RESPONSE_OFFSET = 0x40


class NRC:
    """Negative Response Codes (KWP2000 / ISO 14230-3), subset relevant to GEMS."""

    GENERAL_REJECT = 0x10
    SERVICE_NOT_SUPPORTED = 0x11
    SUBFUNCTION_NOT_SUPPORTED = 0x12
    BUSY_REPEAT_REQUEST = 0x21
    CONDITIONS_NOT_CORRECT = 0x22
    REQUEST_SEQUENCE_ERROR = 0x24
    REQUEST_OUT_OF_RANGE = 0x31
    SECURITY_ACCESS_DENIED = 0x33
    INVALID_KEY = 0x35
    EXCEEDED_ATTEMPTS = 0x36
    RESPONSE_PENDING = 0x78

    NAMES = {
        0x10: "generalReject",
        0x11: "serviceNotSupported",
        0x12: "subFunctionNotSupported",
        0x21: "busyRepeatRequest",
        0x22: "conditionsNotCorrect",
        0x24: "requestSequenceError",
        0x31: "requestOutOfRange",
        0x33: "securityAccessDenied",
        0x35: "invalidKey",
        0x36: "exceededNumberOfAttempts",
        0x78: "responsePending",
    }

    @classmethod
    def name(cls, nrc: int) -> str:
        return cls.NAMES.get(nrc, f"unknown(0x{nrc:02X})")


class NegativeResponse(Exception):
    """Raised when a negative response is received where a positive was required."""

    def __init__(self, service: int, nrc: int):
        self.service = service
        self.nrc = nrc
        super().__init__(
            f"Negative response to service 0x{service:02X}: "
            f"{NRC.name(nrc)} (0x{nrc:02X})"
        )


@dataclass(frozen=True, slots=True)
class Request:
    """A diagnostic request: a service id (SID) plus its payload.

    ``data`` is the sub-function/parameter bytes that follow the SID (it does
    NOT include the SID itself).
    """

    service: int
    data: bytes = b""

    def __post_init__(self) -> None:
        if not 0 <= self.service <= 0xFF:
            raise ValueError(f"service id out of range: {self.service}")

    @property
    def positive_sid(self) -> int:
        """The SID that a positive response to this request will carry."""
        return (self.service + POSITIVE_RESPONSE_OFFSET) & 0xFF

    def hex(self) -> str:
        return bytes([self.service, *self.data]).hex(" ")


@dataclass(frozen=True, slots=True)
class Response:
    """A diagnostic response.

    ``service`` is the *request* SID this answers (e.g. ``0x21``), NOT the
    echoed ``+0x40`` value. For a positive response, ``data`` is the payload
    that followed the echoed SID on the wire. For a negative response,
    ``is_negative`` is True and ``nrc`` is set.
    """

    service: int
    data: bytes = b""
    is_negative: bool = False
    nrc: int | None = None

    @classmethod
    def positive(cls, request_service: int, data: bytes = b"") -> "Response":
        return cls(service=request_service, data=bytes(data), is_negative=False)

    @classmethod
    def negative(cls, request_service: int, nrc: int) -> "Response":
        return cls(service=request_service, data=b"", is_negative=True, nrc=nrc)

    @property
    def nrc_name(self) -> str | None:
        return None if self.nrc is None else NRC.name(self.nrc)

    def ensure_positive(self) -> "Response":
        """Return self if positive, else raise :class:`NegativeResponse`."""
        if self.is_negative:
            raise NegativeResponse(self.service, self.nrc if self.nrc is not None else 0)
        return self
