"""The transport-agnostic KWP2000 client.

``KwpClient`` is the load-bearing seam: it wraps any
:class:`~gems_t4.transport.base.Transport` (a real K-line adapter or the
in-memory :class:`~gems_t4.transport.virtual.VirtualTransport`) and turns
:class:`~gems_t4.protocol.messages.Request` objects into wire frames and back.

It is GENERIC KWP — it knows services by SID but nothing about GEMS meaning
(no import of :mod:`gems_t4.gems`). GEMS decoding lives one layer up.
"""
from __future__ import annotations

from gems_t4.protocol import framing
from gems_t4.protocol.messages import Request, Response
from gems_t4.protocol.timing import TimingPolicy
from gems_t4.transport.base import InitResult, Transport


class ProtocolError(Exception):
    """A well-formed frame whose contents violate an expectation (e.g. the
    echoed local id in a $61 response does not match the one requested)."""


class WirelessWriteRefused(ProtocolError):
    """A write-capable service was attempted over a wireless/network transport.

    Policy (CLAUDE.md): coding writes, actuator commands and Security-Learn stay
    wired-only; network transports are live-data/DTC monitoring only unless the
    transport was built with ``allow_writes=True``.
    """


#: SIDs refused unconditionally over a wireless transport: SecurityAccess
#: (0x27 — only ever a precursor to the blocked writes, and itself mutates ECU
#: security state), ActuatorControl (0x30), WriteDataByLocalId / coding (0x3B).
#: StartRoutine (0x31) is handled per-routine below. Reads — and
#: ClearDiagnosticInformation (0x14), part of the read→diagnose→clear
#: monitoring workflow — stay allowed.
WIRELESS_BLOCKED_SERVICES = frozenset({0x27, 0x30, 0x3B})

#: The one $31 routine that is a pure read: immobiliser STATUS (routine 0x03,
#: per the SID map in INTERFACES.md). The learn routines (0x01 enter-learn,
#: 0x02 store-code) are writes and stay blocked.
_ROUTINE_STATUS = 0x03


def _is_wireless_blocked(req: Request) -> bool:
    """Whether ``req`` is a write-capable service under the wireless policy."""
    if req.service in WIRELESS_BLOCKED_SERVICES:
        return True
    if req.service == 0x31:
        return not (req.data and req.data[0] == _ROUTINE_STATUS)
    return False


class KwpClient:
    """A generic KWP2000 tester bound to one transport and ECU address."""

    def __init__(
        self,
        transport: Transport,
        *,
        ecu_address: int = framing.DEFAULT_ECU_ADDRESS,
        tester_address: int = framing.TESTER_ADDRESS,
        timing: TimingPolicy | None = None,
    ) -> None:
        self.transport = transport
        self.ecu_address = ecu_address
        self.tester_address = tester_address
        self.timing = timing or TimingPolicy()

    # -- lifecycle ---------------------------------------------------------- #
    def connect(self, mode: str = "slow") -> InitResult:
        """Open the transport and perform the ECU init handshake."""
        self.transport.open()
        return self.transport.init(self.ecu_address, mode)

    def close(self) -> None:
        """Close the underlying transport."""
        self.transport.close()

    def __enter__(self) -> "KwpClient":
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- core exchange ------------------------------------------------------ #
    def request(
        self,
        req: Request,
        *,
        timeout: float | None = None,
        expect_positive: bool = False,
    ) -> Response:
        """Send one request and return the decoded response.

        With ``expect_positive=True`` a negative response raises
        :class:`~gems_t4.protocol.messages.NegativeResponse`.

        Write-capable services (:data:`WIRELESS_BLOCKED_SERVICES`, plus the
        $31 learn routines) are refused with :class:`WirelessWriteRefused`
        when the transport reports ``is_wireless`` and was not built with
        ``allow_writes=True``.
        """
        if (
            _is_wireless_blocked(req)
            and getattr(self.transport, "is_wireless", False)
            and not getattr(self.transport, "allow_writes", False)
        ):
            raise WirelessWriteRefused(
                f"service 0x{req.service:02X} refused: writes are wired-only "
                "over a network/wireless transport (enable --allow-writes to "
                "override on a trusted link)"
            )
        frame = framing.encode_request(
            req, ecu_address=self.ecu_address, tester_address=self.tester_address
        )
        self.transport.send(frame)
        resp_frame = self.transport.receive(
            timeout if timeout is not None else self.timing.response_timeout
        )
        resp = framing.decode_response(resp_frame, req.service)
        if expect_positive:
            resp.ensure_positive()
        return resp

    # -- convenience wrappers ---------------------------------------------- #
    def start_session(self, session: int = 0x81) -> Response:
        """StartDiagnosticSession (0x10)."""
        return self.request(Request(0x10, bytes([session])), expect_positive=True)

    def tester_present(self) -> None:
        """TesterPresent (0x3E) keep-alive."""
        self.request(Request(0x3E), expect_positive=True)

    def read_data_by_local_id(self, local_id: int) -> bytes:
        """ReadDataByLocalId (0x21 -> 0x61). Returns the value bytes.

        The echoed local id is validated; the returned bytes are everything
        after it. Raises :class:`ProtocolError` on a mismatched echo and
        :class:`NegativeResponse` on a negative reply.
        """
        resp = self.request(Request(0x21, bytes([local_id])), expect_positive=True)
        if not resp.data or resp.data[0] != local_id:
            got = resp.data[0] if resp.data else None
            raise ProtocolError(
                f"$61 echoed local id {got} does not match requested {local_id}"
            )
        return resp.data[1:]

    def read_dtcs_raw(self) -> bytes:
        """ReadDTCByStatus (0x18). Returns the raw response payload."""
        return self.request(Request(0x18), expect_positive=True).data

    def clear_dtcs(self) -> Response:
        """ClearDiagnosticInformation (0x14)."""
        return self.request(Request(0x14), expect_positive=True)

    def security_access(self, key_fn) -> None:
        """SecurityAccess (0x27): request seed, compute key via ``key_fn``, send.

        ``key_fn`` maps an int seed to an int key (e.g.
        :func:`gems_t4.protocol.security.compute_key`).
        """
        seed_resp = self.request(Request(0x27, bytes([0x01])), expect_positive=True)
        d = seed_resp.data
        if len(d) < 3:
            raise ProtocolError("seed response too short")
        seed = (d[1] << 8) | d[2]
        key = key_fn(seed) & 0xFFFF
        self.request(
            Request(0x27, bytes([0x02, (key >> 8) & 0xFF, key & 0xFF])),
            expect_positive=True,
        )

    def write_data_by_local_id(self, local_id: int, value: bytes) -> Response:
        """WriteDataByLocalId (0x3B) — coding writes."""
        return self.request(
            Request(0x3B, bytes([local_id, *value])), expect_positive=True
        )

    def actuator(self, actuator_id: int, state: int) -> Response:
        """ActuatorControl (0x30). Returns the raw Response (may be negative:
        a refusal such as "engine running" comes back as CONDITIONS_NOT_CORRECT)."""
        return self.request(Request(0x30, bytes([actuator_id, state])))

    def start_routine(
        self, routine_id: int, data: bytes = b"", *, expect_positive: bool = False
    ) -> Response:
        """StartRoutineByLocalId (0x31) — used for the Security-Learn immobiliser
        re-sync routines. Returns the raw Response (callers inspect negatives such
        as SECURITY_ACCESS_DENIED / REQUEST_SEQUENCE_ERROR) unless
        ``expect_positive`` is set."""
        return self.request(
            Request(0x31, bytes([routine_id, *data])), expect_positive=expect_positive
        )
