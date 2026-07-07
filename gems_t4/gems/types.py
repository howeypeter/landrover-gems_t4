"""Shared GEMS domain value objects, used across the dtc/livedata/actuator/
virtual-ECU/CLI modules. Defined centrally so every layer agrees on their shape.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DtcState(str, Enum):
    """Whether a stored fault is currently active or historic."""

    ACTIVE = "active"
    STORED = "stored"
    PENDING = "pending"


@dataclass(frozen=True, slots=True)
class Dtc:
    """A diagnostic trouble code as presented to the technician.

    ``code`` is the 5-char P-code (e.g. ``"P0118"``). ``description`` is the
    RAVE/TestBook-style text. ``raw`` is the ECU's internal 2-byte identifier
    for this code (the emulator assigns coherent raw ids; see gems/dtc.py).
    """

    code: str
    description: str
    raw: int = 0
    state: DtcState = DtcState.STORED


@dataclass(frozen=True, slots=True)
class Measure:
    """One decoded live-data value.

    ``name`` is the display label (e.g. ``"Coolant temperature"``); ``value`` is
    the engineering value; ``unit`` is e.g. ``"degC"``, ``"rpm"``, ``"V"``;
    ``raw`` is the undecoded integer as it appeared in the $61 record.
    """

    name: str
    value: float | int | str
    unit: str = ""
    raw: int = 0

    def formatted(self) -> str:
        if isinstance(self.value, float):
            body = f"{self.value:.2f}"
        else:
            body = str(self.value)
        return f"{body} {self.unit}".strip()


@dataclass(frozen=True, slots=True)
class ActuatorOutcome:
    """Result of an actuator-test request.

    ``ok`` False with a ``message`` models the characterful T4 refusals
    (e.g. "Test not available — engine running").
    """

    actuator_id: int
    ok: bool
    message: str = ""
