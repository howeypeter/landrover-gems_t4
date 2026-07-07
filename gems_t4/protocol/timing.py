"""KWP2000 / ISO-14230 timing policy.

The K-line is a slow, half-duplex, tester-initiated bus; several inter-byte and
turnaround windows (P1..P4) govern how a real adapter must pace bytes. Those
windows only *matter* to timing-aware code — the real transports and firmware.
This module is a pure data container: it names the windows and supplies sane
KWP defaults. Nothing here sleeps or does I/O.

The generic :class:`~gems_t4.protocol.client.KwpClient` only uses
:attr:`TimingPolicy.response_timeout` (as the default ``timeout`` it passes to
``transport.receive``); the P1..P4 fields are consumed by real transports.

Reference (all seconds):

======  =========================================================  ===========
Field   Meaning                                                    KWP typical
======  =========================================================  ===========
p1      inter-byte time within an ECU response                     0..0.020
p2      request-end -> response-start turnaround                   0.025..0.050
p3      response-end -> next-request minimum gap                   0.055 (min)
p4      inter-byte time within a tester request                    0.005..0.020
======  =========================================================  ===========
"""
from __future__ import annotations

from dataclasses import dataclass

__all__ = ["TimingPolicy"]


@dataclass(frozen=True, slots=True)
class TimingPolicy:
    """Inter-byte / turnaround windows for a K-line link, in seconds.

    Defaults follow common KWP2000 / ISO-14230 values. ``p3`` is the *minimum*
    gap between the end of a response and the start of the next request;
    ``response_timeout`` is the wall-clock budget a client allows for a full
    response to arrive before treating the link as timed out.
    """

    #: Inter-byte time within an ECU response (max), seconds.
    p1: float = 0.020
    #: Request-end to response-start turnaround (max), seconds.
    p2: float = 0.050
    #: Minimum response-end to next-request gap, seconds.
    p3: float = 0.055
    #: Inter-byte time within a tester request (max), seconds.
    p4: float = 0.020
    #: Overall budget for a complete response to arrive, seconds.
    response_timeout: float = 1.0

    def as_milliseconds(self) -> tuple[int, int, int, int]:
        """Return ``(P1, P2, P3, P4)`` rounded to whole milliseconds.

        Convenient for the ``SET_TIMING`` host-protocol command, which encodes
        each window as a ``uint16`` millisecond value.
        """
        return (
            round(self.p1 * 1000),
            round(self.p2 * 1000),
            round(self.p3 * 1000),
            round(self.p4 * 1000),
        )
