"""The ECU-handler contract that the virtual ECU implements and that the
virtual transport consumes.

Keeping this a ``Protocol`` (structural type) means ``VirtualTransport`` depends
only on this interface, not on the concrete ``VirtualEcu`` — the CLI wires a
concrete ECU into a transport at run time.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from gems_t4.protocol.messages import Request, Response


@runtime_checkable
class EcuHandler(Protocol):
    """Anything that can answer diagnostic requests like an ECU."""

    def handle(self, request: Request) -> Response:
        """Process one request and return the response (positive or negative)."""
        ...

    def tick(self, dt: float) -> None:
        """Advance internal simulation time by ``dt`` seconds (warm-up, idle hunt).

        A no-op is a valid implementation for a static ECU.
        """
        ...
