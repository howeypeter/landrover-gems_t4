"""Static profile of the GEMS engine ECU: address, keybytes, identity, and the
set of services/local-ids it supports. Used to configure the client/virtual ECU
and to drive VIN-first "which systems are fitted" logic later.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class EcuProfile:
    """Identifying facts about an ECU on the K-line."""

    name: str
    ecu_address: int
    keybytes: bytes
    vehicle: str
    supported_sids: frozenset[int] = field(default_factory=frozenset)


#: The Lucas/SAGEM GEMS V8 engine ECU (P38 Range Rover / Discovery 1).
GEMS_PROFILE = EcuProfile(
    name="Lucas/SAGEM GEMS 8 (engine)",
    ecu_address=0x10,
    keybytes=b"\x08\x08",
    vehicle="P38 Range Rover 4.0/4.6 V8 (1995-1999)",
    supported_sids=frozenset(
        {0x10, 0x14, 0x18, 0x1A, 0x21, 0x27, 0x30, 0x3B, 0x3E}
    ),
)
