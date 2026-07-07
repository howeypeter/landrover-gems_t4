"""Display specs for the live-data gauges: scale range, redline, and preferred
widget style per parameter.

A gauge's *scale* (0–7000 rpm, a redline at 6000, etc.) is a presentation
decision, so it lives in the GUI layer rather than in ``gems/livedata`` — the
protocol/gems code stays free of display concerns. Screens look a spec up by the
parameter's local id; parameters without an explicit spec get a sensible dial
synthesised from their nominal value.
"""
from __future__ import annotations

from dataclasses import dataclass

from gems_t4.gems.livedata import PARAMETERS

# Widget styles a spec can request.
STYLE_DIAL = "dial"   # analog dial + needle (continuous numeric)
STYLE_BAR = "bar"     # horizontal bar (0..100 %-style)
STYLE_LCD = "lcd"     # amber numeric/enum readout (flags, enums)


@dataclass(frozen=True, slots=True)
class GaugeSpec:
    """How one live parameter is drawn as a gauge."""

    local_id: int
    label: str
    unit: str
    vmin: float
    vmax: float
    redline: float | None = None
    decimals: int = 0
    style: str = STYLE_DIAL


# Explicit specs for the main measures (local id -> spec).
_SPECS: tuple[GaugeSpec, ...] = (
    GaugeSpec(0x01, "Coolant", "degC", -40, 120, redline=110, decimals=0),
    GaugeSpec(0x02, "Engine speed", "rpm", 0, 7000, redline=6000, decimals=0),
    GaugeSpec(0x03, "Battery", "V", 8, 16, redline=15, decimals=1),
    GaugeSpec(0x04, "Throttle", "%", 0, 100, decimals=0, style=STYLE_BAR),
    GaugeSpec(0x05, "Mass air flow", "kg/h", 0, 260, decimals=0),
    GaugeSpec(0x06, "Intake air", "degC", -20, 90, decimals=0),
    GaugeSpec(0x07, "O2 bank A", "V", 0.0, 1.0, decimals=2),
    GaugeSpec(0x08, "STFT", "%", -25, 25, decimals=0),
    GaugeSpec(0x09, "LTFT", "%", -25, 25, decimals=0),
    GaugeSpec(0x0A, "IACV steps", "", 0, 200, decimals=0),
    GaugeSpec(0x0B, "Ignition adv", "deg", -10, 45, decimals=0),
    GaugeSpec(0x0C, "Road speed", "mph", 0, 120, decimals=0),
    GaugeSpec(0x0D, "Loop status", "", 0, 2, decimals=0, style=STYLE_LCD),
    GaugeSpec(0x0E, "Misfire total", "", 0, 200, redline=50, decimals=0),
    GaugeSpec(0x0F, "Fuel temp", "degC", -40, 120, decimals=0),
    GaugeSpec(0x10, "Idle target", "rpm", 0, 2000, decimals=0),
    GaugeSpec(0x11, "Calc load", "%", 0, 100, decimals=0, style=STYLE_BAR),
    GaugeSpec(0x12, "O2 bank B", "V", 0.0, 1.0, decimals=2),
    GaugeSpec(0x13, "Gearbox D/P", "", 0, 1, decimals=0, style=STYLE_LCD),
    GaugeSpec(0x14, "A/C request", "", 0, 1, decimals=0, style=STYLE_LCD),
    GaugeSpec(0x15, "Ignition sw", "", 0, 1, decimals=0, style=STYLE_LCD),
    GaugeSpec(0x16, "Gbx retard", "%", 0, 100, decimals=0, style=STYLE_BAR),
    GaugeSpec(0x19, "Security learn", "", 0, 1, decimals=0, style=STYLE_LCD),
    GaugeSpec(0x1A, "Mobilised", "", 0, 1, decimals=0, style=STYLE_LCD),
)

GAUGE_SPECS: dict[int, GaugeSpec] = {s.local_id: s for s in _SPECS}


def spec_for(local_id: int) -> GaugeSpec:
    """Return the gauge spec for a parameter, synthesising a dial if none exists."""
    spec = GAUGE_SPECS.get(local_id)
    if spec is not None:
        return spec
    p = PARAMETERS.get(local_id)
    if p is None:
        return GaugeSpec(local_id, f"id 0x{local_id:02X}", "", 0, 100)
    nominal = p.nominal if isinstance(p.nominal, (int, float)) else 0
    vmax = max(1.0, float(nominal) * 2.0)
    return GaugeSpec(local_id, p.name, p.unit, 0, vmax, decimals=0)
