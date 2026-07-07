"""K-line initialization constants (pure data, no I/O).

Three init families reach a GEMS-era ECU (see
``memory/research/kline-protocols.md``). The wake/handshake itself is
timing-critical and therefore lives in the real transport / firmware; this
module only names the addresses, modes, and canonical bytes those
implementations reference. Nothing here touches hardware or sleeps.
"""
from __future__ import annotations

from enum import Enum

__all__ = [
    "GENERIC_INIT_ADDRESS",
    "ROVER_INIT_ADDRESS",
    "SYNC_BYTE",
    "DEFAULT_KEYBYTES",
    "InitMode",
    "normalize_mode",
    "invert_byte",
]

#: 5-baud init address for OBD-II generic access (ISO 9141-2).
GENERIC_INIT_ADDRESS = 0x33

#: 5-baud init address for Rover-native (full dealer) access.
ROVER_INIT_ADDRESS = 0x16

#: Sync byte the ECU returns after receiving the 5-baud address (0x55).
SYNC_BYTE = 0x55

#: Placeholder keybytes reported by a successful init when none are known.
DEFAULT_KEYBYTES = b"\x08\x08"


class InitMode(str, Enum):
    """The two init pacing families the transports understand.

    * :attr:`SLOW` — 5-baud address transmission (ISO 9141-2 style).
    * :attr:`FAST` — the 25 ms low / 25 ms high wake pulse (ISO 14230-2 /
      KWP2000 fast init).
    """

    SLOW = "slow"
    FAST = "fast"


def normalize_mode(mode: str | InitMode) -> InitMode:
    """Coerce a ``"slow"``/``"fast"`` string (or :class:`InitMode`) safely.

    Raises
    ------
    ValueError
        If ``mode`` is not a recognized init mode.
    """
    if isinstance(mode, InitMode):
        return mode
    try:
        return InitMode(str(mode).lower())
    except ValueError as exc:  # pragma: no cover - trivial re-raise
        valid = ", ".join(m.value for m in InitMode)
        raise ValueError(f"unknown init mode {mode!r} (expected one of: {valid})") from exc


def invert_byte(value: int) -> int:
    """Return the bitwise-inverted low byte of ``value``.

    The 5-baud handshake exchanges an inverted keybyte and an inverted address;
    this is the (pure) helper the transport uses to compute them.
    """
    return (~value) & 0xFF
