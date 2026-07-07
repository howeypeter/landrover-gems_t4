"""GEMS fuel / ignition maps — data for the "map editor" lookalike.

REALITY (gems-hardware.md): GEMS calibration lives in two socketed UV-EPROMs and
is **not** reflashable over the K-line — that path never existed for GEMS. Real
remapping is a bench chip swap: pull the 27C512 (fuel) / 27C1001 (ignition +
code), read/edit/burn, refit. So this module is a faithful *lookalike*: it
surfaces the maps as viewable 16x16 tables and the chip facts, with the honest
note that changing them means swapping chips, not writing over the port. The
table values here are plausible synthetic surfaces, not a dumped real ROM.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EpromChip:
    """One socketed UV-EPROM in the GEMS ECU."""

    part: str
    size_kb: int
    holds: str


#: The two GEMS EPROMs (see gems-hardware.md).
FUEL_EPROM = EpromChip("27C512", 64, "Fuel maps + fuelling calibration")
IGNITION_EPROM = EpromChip("27C1001", 128, "Ignition maps + main program code")

#: Why there is no "write" button here.
CHIP_SWAP_NOTE = (
    "GEMS maps live in two socketed UV-EPROMs (27C512 fuel, 27C1001 ignition) - "
    "there is no K-line reflash path for GEMS. Changing a map is a bench operation: "
    "remove the ECU, swap/burn the EPROM, refit. This screen is a read-only "
    "lookalike; the real T4 had no GEMS calibration write either."
)

#: 16 RPM breakpoints (map columns), rev/min.
RPM_AXIS: tuple[int, ...] = tuple(500 + i * 350 for i in range(16))  # 500..5750
#: 16 load breakpoints (map rows), % engine load.
LOAD_AXIS: tuple[int, ...] = tuple(round(6.25 * (i + 1)) for i in range(16))  # ~6..100


@dataclass(frozen=True, slots=True)
class MapTable:
    """A 16x16 calibration table with axis breakpoints."""

    name: str
    unit: str
    rpm_axis: tuple[int, ...]
    load_axis: tuple[int, ...]
    cells: tuple[tuple[float, ...], ...]  # [load_row][rpm_col]

    @property
    def rows(self) -> int:
        return len(self.cells)

    @property
    def cols(self) -> int:
        return len(self.cells[0]) if self.cells else 0

    def cell(self, load_row: int, rpm_col: int) -> float:
        return self.cells[load_row][rpm_col]


def _fuel_cells() -> tuple[tuple[float, ...], ...]:
    """Injector pulse-width (ms) rising with load, tapering slightly at high rpm."""
    rows = []
    for r in range(16):
        load = (r + 1) / 16.0
        row = []
        for c in range(16):
            rpm_frac = c / 15.0
            base = 2.0 + 12.0 * load          # more load -> more fuel
            taper = 1.0 - 0.15 * rpm_frac     # slight high-rpm taper
            row.append(round(base * taper, 2))
        rows.append(tuple(row))
    return tuple(rows)


def _ignition_cells() -> tuple[tuple[float, ...], ...]:
    """Spark advance (deg BTDC) rising with rpm, pulled back under high load."""
    rows = []
    for r in range(16):
        load = (r + 1) / 16.0
        row = []
        for c in range(16):
            rpm_frac = c / 15.0
            adv = 8.0 + 30.0 * rpm_frac - 14.0 * load  # more rpm advance, less under load
            row.append(round(max(4.0, adv), 1))
        rows.append(tuple(row))
    return tuple(rows)


FUEL_MAP = MapTable(
    name="Fuel — injector pulse width",
    unit="ms",
    rpm_axis=RPM_AXIS,
    load_axis=LOAD_AXIS,
    cells=_fuel_cells(),
)

IGNITION_MAP = MapTable(
    name="Ignition — spark advance",
    unit="deg BTDC",
    rpm_axis=RPM_AXIS,
    load_axis=LOAD_AXIS,
    cells=_ignition_cells(),
)

#: All maps, keyed by a short token.
MAPS: dict[str, MapTable] = {"fuel": FUEL_MAP, "ignition": IGNITION_MAP}
