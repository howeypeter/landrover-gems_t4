"""GEMS $61 live-data records.

Each live parameter has a one-byte local id read via KWP ReadDataByLocalId
(0x21 -> 0x61). A :class:`ParamDef` knows how to turn an engineering value into
the raw bytes on the wire and back into a :class:`~gems_t4.gems.types.Measure`.

The two emulator-only fields ``state_key`` and ``nominal`` let the virtual ECU
build its baseline state and answer reads from a single source of truth; they do
not affect the wire encoding.

This is a representative ~24-parameter subset of the ~35 GEMS live measures in
``memory/research/gems-data-catalog.md`` (coolant/fuel/air temps, RPM, MAF,
throttle, O2, fuel trims, IACV steps, road speed, loop status, misfire count,
immobiliser state, ...). More can be appended without touching other modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from gems_t4.gems.types import Measure

if TYPE_CHECKING:  # pragma: no cover
    from gems_t4.protocol.client import KwpClient

#: Numeric encoding of the fuelling loop-status enum (see the virtual ECU).
LOOP_MAP: dict[str, int] = {"open": 0, "closed": 1, "open_fault": 2}
LOOP_NAMES: dict[int, str] = {v: k for k, v in LOOP_MAP.items()}


@dataclass(frozen=True, slots=True)
class ParamDef:
    """Definition of one $61 live measure.

    Wire mapping: ``value = raw * scale + offset``. ``encode`` inverts that and
    clamps to the representable range so it never raises on extreme inputs.
    """

    local_id: int
    name: str
    unit: str
    nbytes: int = 1
    scale: float = 1.0
    offset: float = 0.0
    signed: bool = False
    state_key: str = ""
    nominal: float | str = 0.0

    def _raw_bounds(self) -> tuple[int, int]:
        bits = 8 * self.nbytes
        if self.signed:
            return -(1 << (bits - 1)), (1 << (bits - 1)) - 1
        return 0, (1 << bits) - 1

    def encode(self, value: float) -> bytes:
        """Engineering value -> raw big-endian bytes (clamped to range)."""
        raw = round((value - self.offset) / self.scale)
        lo, hi = self._raw_bounds()
        raw = max(lo, min(hi, raw))
        return raw.to_bytes(self.nbytes, "big", signed=self.signed)

    def decode(self, raw: bytes) -> Measure:
        """Raw bytes -> :class:`Measure`."""
        raw_int = int.from_bytes(raw, "big", signed=self.signed)
        value = raw_int * self.scale + self.offset
        # keep ints tidy when scale is integral
        if float(value).is_integer():
            value = int(value)
        else:
            value = round(value, 3)
        return Measure(name=self.name, value=value, unit=self.unit, raw=raw_int)


_DEFS: tuple[ParamDef, ...] = (
    ParamDef(0x01, "Coolant temperature", "degC", 1, 1.0, -40.0, False, "coolant_temp", 85),
    ParamDef(0x02, "Engine speed", "rpm", 2, 0.25, 0.0, False, "rpm", 750),
    ParamDef(0x03, "Battery voltage", "V", 1, 0.1, 0.0, False, "battery", 13.8),
    ParamDef(0x04, "Throttle angle", "%", 1, 0.5, 0.0, False, "throttle", 3.0),
    ParamDef(0x05, "Mass air flow", "kg/h", 1, 1.0, 0.0, False, "maf", 22),
    ParamDef(0x06, "Intake air temperature", "degC", 1, 1.0, -40.0, False, "intake_air_temp", 30),
    ParamDef(0x07, "O2 sensor voltage (bank A)", "V", 1, 0.01, 0.0, False, "o2_voltage", 0.45),
    ParamDef(0x08, "Short-term fuel trim", "%", 1, 1.0, 0.0, True, "fuel_trim_short", 0),
    ParamDef(0x09, "Long-term fuel trim", "%", 1, 1.0, 0.0, True, "fuel_trim_long", 0),
    ParamDef(0x0A, "Idle air control valve", "steps", 1, 1.0, 0.0, False, "iacv_steps", 20),
    ParamDef(0x0B, "Ignition advance", "deg", 1, 0.5, 0.0, True, "ignition_advance", 12),
    ParamDef(0x0C, "Road speed", "mph", 1, 1.0, 0.0, False, "road_speed", 0),
    ParamDef(0x0D, "Fuelling loop status", "", 1, 1.0, 0.0, False, "loop_status", "closed"),
    ParamDef(0x0E, "Misfire count (total)", "", 2, 1.0, 0.0, False, "misfire_total", 0),
    ParamDef(0x0F, "Fuel temperature", "degC", 1, 1.0, -40.0, False, "fuel_temp", 40),
    ParamDef(0x10, "Idle speed reference", "rpm", 2, 0.25, 0.0, False, "idle_target", 750),
    ParamDef(0x11, "Calculated load", "%", 1, 0.5, 0.0, False, "calc_load", 25),
    ParamDef(0x12, "O2 sensor voltage (bank B)", "V", 1, 0.01, 0.0, False, "o2_voltage_b2", 0.45),
    ParamDef(0x13, "Gearbox status (0=P,1=D)", "", 1, 1.0, 0.0, False, "gearbox_status", 0),
    ParamDef(0x14, "A/C request", "", 1, 1.0, 0.0, False, "ac_request", 0),
    ParamDef(0x15, "Ignition switch", "", 1, 1.0, 0.0, False, "ignition_switch", 1),
    ParamDef(0x16, "Gearbox torque retard", "%", 1, 1.0, 0.0, False, "gearbox_retard", 17),
    ParamDef(0x19, "Security learn state", "", 1, 1.0, 0.0, False, "security_learn", 1),
    ParamDef(0x1A, "Immobiliser mobilised", "", 1, 1.0, 0.0, False, "mobilised", 1),
)

#: All live-data parameters, keyed by local id.
PARAMETERS: dict[int, ParamDef] = {p.local_id: p for p in _DEFS}


def decode_measure(local_id: int, raw: bytes) -> Measure:
    """Decode raw value bytes for ``local_id`` into a :class:`Measure`.

    Unknown ids yield a generic Measure so a surprising ECU never crashes the
    reader.
    """
    p = PARAMETERS.get(local_id)
    if p is None:
        return Measure(
            name=f"Unknown (id 0x{local_id:02X})",
            value=int.from_bytes(raw, "big") if raw else 0,
            unit="",
            raw=int.from_bytes(raw, "big") if raw else 0,
        )
    return p.decode(raw)


def read_all(client: "KwpClient", ids: list[int] | None = None) -> list[Measure]:
    """Read a set of live measures from the ECU (defaults to all known ids)."""
    ids = ids if ids is not None else list(PARAMETERS)
    out: list[Measure] = []
    for local_id in ids:
        raw = client.read_data_by_local_id(local_id)
        out.append(decode_measure(local_id, raw))
    return out
