"""In-memory transport backed by a virtual ECU — the off-car test seam.

``VirtualTransport`` is a drop-in for a real K-line adapter: it carries whole
KWP frames, but instead of a serial port it decodes each request frame, hands
the :class:`~gems_t4.protocol.messages.Request` to an
:class:`~gems_t4.gems.ecu_base.EcuHandler`, and re-encodes the resulting
:class:`~gems_t4.protocol.messages.Response` into a response frame. Because the
whole stack above the transport is pure logic, the entire client/protocol/gems
stack becomes testable with no hardware and no real serial port.

Per the build contract this module may import ``protocol.framing`` and
``gems.ecu_base`` only — never ``protocol.client`` or the rest of ``gems``.

Timing note: the default path is *instant*. ``latency`` defaults to ``0.0`` and
no real ``time.sleep`` runs unless a caller explicitly asks for latency > 0
(used only to model authentic ISO 9141 slowness in an interactive app, never in
tests).
"""
from __future__ import annotations

import time

from gems_t4.gems.ecu_base import EcuHandler
from gems_t4.protocol import framing
from gems_t4.transport.base import (
    InitResult,
    Transport,
    TransportClosed,
    TransportTimeout,
)


class VirtualTransport(Transport):
    """A :class:`Transport` that answers from an in-memory ECU handler.

    Parameters
    ----------
    ecu:
        Anything implementing :class:`~gems_t4.gems.ecu_base.EcuHandler` (the
        virtual ECU, or a tiny fake in tests). Its :meth:`~EcuHandler.handle`
        is called with the decoded request.
    latency:
        Optional per-exchange delay in seconds, applied on
        :meth:`receive` to model K-line/USB slowness. Defaults to ``0.0`` — no
        real sleep occurs on the default (test) path.
    """

    def __init__(self, ecu: EcuHandler, *, latency: float = 0.0) -> None:
        if latency < 0:
            raise ValueError(f"latency must be >= 0, got {latency}")
        self._ecu = ecu
        self._latency = float(latency)
        self._open = False
        #: Buffered response frame produced by the last :meth:`send`, consumed
        #: by the next :meth:`receive`. ``None`` means nothing to read.
        self._pending: bytes | None = None

    # -- lifecycle ---------------------------------------------------------- #
    def open(self) -> None:
        """Mark the transport open. Trivial for the in-memory ECU."""
        self._open = True

    def close(self) -> None:
        """Mark the transport closed. Idempotent."""
        self._open = False
        self._pending = None

    def is_open(self) -> bool:
        """Return whether the transport is currently open."""
        return self._open

    def init(self, address: int, mode: str = "slow") -> InitResult:
        """Perform the (trivial) virtual wake/handshake.

        There is no real K-line to sync, so this simply ensures the transport
        is open and returns a canned :class:`InitResult`. ``address`` and
        ``mode`` are accepted for interface parity with real transports.
        """
        if not self._open:
            self.open()
        return InitResult()

    # -- data path ---------------------------------------------------------- #
    def send(self, frame: bytes) -> None:
        """Decode ``frame``, run it through the ECU, buffer the response.

        The request frame is decoded with :func:`framing.decode_request`, the
        resulting :class:`Request` is passed to ``ecu.handle``, and the
        returned :class:`Response` is encoded with
        :func:`framing.encode_response` and buffered for the next
        :meth:`receive`.
        """
        if not self._open:
            raise TransportClosed("send() on a closed VirtualTransport")
        request = framing.decode_request(frame)
        response = self._ecu.handle(request)
        self._pending = framing.encode_response(response)

    def receive(self, timeout: float | None = None) -> bytes:
        """Return the buffered response frame, or raise on nothing pending.

        Raises
        ------
        TransportClosed
            If the transport is not open.
        TransportTimeout
            If :meth:`send` has not produced a response frame to read.
        """
        if not self._open:
            raise TransportClosed("receive() on a closed VirtualTransport")
        if self._pending is None:
            raise TransportTimeout("no buffered response to receive")
        # Only sleep when a caller explicitly opted into modeled latency;
        # the default/test path (latency == 0.0) never touches the clock.
        if self._latency > 0:
            time.sleep(self._latency)
        frame = self._pending
        self._pending = None
        return frame
