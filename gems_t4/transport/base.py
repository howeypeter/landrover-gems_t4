"""The Transport abstraction — the load-bearing seam of the whole stack.

``KwpClient`` talks to a ``Transport`` in raw bytes: it hands over a fully-built
KWP frame and gets back the ECU's raw response frame. Everything above the
transport is pure logic and identical whether the transport is a real K-line
adapter or the in-memory virtual ECU. This mirrors udsoncan's
Connection/Client split.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass


class TransportError(Exception):
    """Base class for transport failures."""


class TransportTimeout(TransportError):
    """No (complete) response arrived within the timeout."""


class TransportClosed(TransportError):
    """Operation attempted on a transport that is not open."""


class InitError(TransportError):
    """The init/handshake with the ECU failed (no sync byte, bad keybytes...)."""


@dataclass(frozen=True, slots=True)
class InitResult:
    """Result of a successful init handshake."""

    keybytes: bytes = b"\x08\x08"
    baud: int = 10400
    protocol: str = "KWP2000"


class Transport(abc.ABC):
    """Moves complete KWP frames to/from an ECU.

    Contract:

    * ``send(frame)`` transmits one complete KWP message (header..checksum).
    * ``receive(timeout)`` returns exactly one complete response message, or
      raises :class:`TransportTimeout`. Message-boundary detection (inter-byte
      timeout on real hardware) is the transport's concern, not the client's.
    * ``init(address, mode)`` performs the wake/handshake and returns an
      :class:`InitResult`. On a smart adapter this is a firmware command; on the
      virtual ECU it is trivial.
    * Implementations must tolerate ``close()`` on an already-closed transport.
    """

    @abc.abstractmethod
    def open(self) -> None:
        """Acquire the underlying resource (open the serial port, etc.)."""

    @abc.abstractmethod
    def close(self) -> None:
        """Release the underlying resource. Idempotent."""

    @abc.abstractmethod
    def is_open(self) -> bool:
        ...

    @abc.abstractmethod
    def init(self, address: int, mode: str = "slow") -> InitResult:
        """Perform the ECU wake/handshake. ``mode`` is ``"slow"`` or ``"fast"``."""

    @abc.abstractmethod
    def send(self, frame: bytes) -> None:
        """Transmit one complete KWP frame."""

    @abc.abstractmethod
    def receive(self, timeout: float | None = None) -> bytes:
        """Return one complete response frame, or raise :class:`TransportTimeout`."""

    def __enter__(self) -> "Transport":
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
