"""Custom-painted gauge widgets for the live-data screen.

Three widget styles, one interface — every gauge takes a
:class:`~gems_t4.app.gui.gauge_specs.GaugeSpec` and exposes ``set_value`` /
``value``:

* :class:`DialGauge` — an analog dial with a swept scale, redline zone, and needle.
* :class:`BarGauge` — a horizontal bar (for 0..100 %-style measures).
* :class:`LcdReadout` — an amber numeric/enum readout (flags, loop status, ...).

Painting is done with :class:`QPainter`; the widgets are pure presentation and
carry no protocol/gems dependency beyond the spec dataclass. ``build_gauge``
picks the widget class from ``spec.style``.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

# Fixed gauge footprints so the live-data grid lays out predictably (4 per row
# fits the 800px kiosk). Dials are tall; bars/LCDs are short.
_DIAL_W, _DIAL_H = 184, 150
_BAR_W, _BAR_H = 184, 66

from gems_t4.app.gui.gauge_specs import (
    STYLE_BAR,
    STYLE_LCD,
    GaugeSpec,
)

# Palette (kept local so gauges paint consistently; mirrors style.py intent).
_FACE = QColor("#f2f0e8")
_INK = QColor("#23231f")
_MUTED = QColor("#6b6a63")
_SCALE = QColor("#55564f")
_NEEDLE = QColor("#a5140a")
_RED = QColor("#c62828")
_ACCENT = QColor("#1f6b4c")
_LCD_BG = QColor("#20241f")
_LCD_AMBER = QColor("#ffb300")
_BAR_FILL = QColor("#1f6b4c")


class _GaugeBase(QWidget):
    """Shared value/clamp/format logic for every gauge style."""

    def __init__(self, spec: GaugeSpec, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._spec = spec
        self._value: float = float(spec.vmin)
        self.setFixedSize(_DIAL_W, _DIAL_H)

    @property
    def spec(self) -> GaugeSpec:
        return self._spec

    def value(self) -> float:
        return self._value

    def set_value(self, value: float | int | str) -> None:
        """Set the displayed value (coerced to float, clamped to the scale)."""
        try:
            v = float(value)
        except (TypeError, ValueError):
            v = self._spec.vmin
        lo, hi = self._spec.vmin, self._spec.vmax
        self._value = min(hi, max(lo, v))
        self.update()

    def _fraction(self) -> float:
        lo, hi = self._spec.vmin, self._spec.vmax
        if hi <= lo:
            return 0.0
        return (self._value - lo) / (hi - lo)

    def _format(self) -> str:
        return f"{self._value:.{self._spec.decimals}f}"


class DialGauge(_GaugeBase):
    """Analog dial with a 270° swept scale, optional redline, and a needle."""

    _START_DEG = 225.0   # scale start (lower-left), math angle (0=east, CCW+)
    _SWEEP_DEG = 270.0   # clockwise sweep to lower-right

    def paintEvent(self, _event) -> None:  # noqa: N802 (Qt signature)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        side = min(w, h - 18)
        cx, cy = w / 2.0, (h - 12) / 2.0 + 4
        r = side / 2.0 - 6
        face = QRectF(cx - r, cy - r, 2 * r, 2 * r)

        # face
        p.setPen(QPen(_MUTED, 1))
        p.setBrush(_FACE)
        p.drawEllipse(face)

        # scale arc (Qt angles: 1/16 deg, CCW positive)
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(_SCALE, 4))
        p.drawArc(face, int(self._START_DEG * 16), int(-self._SWEEP_DEG * 16))

        # redline zone
        if self._spec.redline is not None:
            lo, hi = self._spec.vmin, self._spec.vmax
            if hi > lo:
                rf = min(1.0, max(0.0, (self._spec.redline - lo) / (hi - lo)))
                start = self._START_DEG - self._SWEEP_DEG * rf
                span = -(self._SWEEP_DEG * (1.0 - rf))
                p.setPen(QPen(_RED, 4))
                p.drawArc(face, int(start * 16), int(span * 16))

        # needle
        ang = math.radians(self._START_DEG - self._SWEEP_DEG * self._fraction())
        tip = QPointF(cx + (r - 8) * math.cos(ang), cy - (r - 8) * math.sin(ang))
        p.setPen(QPen(_NEEDLE, 3, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(QPointF(cx, cy), tip)
        p.setPen(Qt.NoPen)
        p.setBrush(_INK)
        p.drawEllipse(QPointF(cx, cy), 4, 4)

        # label (top) and value+unit (bottom)
        p.setPen(_MUTED)
        f = QFont(self.font()); f.setPointSize(8)
        p.setFont(f)
        p.drawText(QRectF(0, 2, w, 14), Qt.AlignCenter, self._spec.label)

        p.setPen(_INK)
        vf = QFont(self.font()); vf.setPointSize(11); vf.setBold(True)
        p.setFont(vf)
        text = self._format() + (f" {self._spec.unit}" if self._spec.unit else "")
        p.drawText(QRectF(0, h - 20, w, 18), Qt.AlignCenter, text)
        p.end()


class BarGauge(_GaugeBase):
    """Horizontal bar with a fill proportional to value (for %-style measures)."""

    def __init__(self, spec: GaugeSpec, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent)
        self.setFixedSize(_BAR_W, _BAR_H)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(_MUTED)
        f = QFont(self.font()); f.setPointSize(8)
        p.setFont(f)
        p.drawText(QRectF(6, 2, w - 12, 14), Qt.AlignLeft | Qt.AlignVCenter, self._spec.label)
        text = self._format() + (f" {self._spec.unit}" if self._spec.unit else "")
        p.setPen(_INK)
        p.drawText(QRectF(6, 2, w - 12, 14), Qt.AlignRight | Qt.AlignVCenter, text)

        track = QRectF(6, h / 2.0, w - 12, h / 3.0)
        p.setPen(QPen(_MUTED, 1))
        p.setBrush(QColor("#ffffff"))
        p.drawRoundedRect(track, 3, 3)

        fill = QRectF(track)
        fill.setWidth(track.width() * self._fraction())
        over = self._spec.redline is not None and self._value >= self._spec.redline
        p.setPen(Qt.NoPen)
        p.setBrush(_RED if over else _BAR_FILL)
        p.drawRoundedRect(fill, 3, 3)
        p.end()


class LcdReadout(_GaugeBase):
    """Amber numeric / enum readout on a dark panel (flags, loop status, ...)."""

    def __init__(self, spec: GaugeSpec, parent: QWidget | None = None) -> None:
        super().__init__(spec, parent)
        self.setFixedSize(_BAR_W, _BAR_H)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        p.setPen(_MUTED)
        f = QFont(self.font()); f.setPointSize(8)
        p.setFont(f)
        p.drawText(QRectF(4, 2, w - 8, 14), Qt.AlignCenter, self._spec.label)

        panel = QRectF(6, 18, w - 12, h - 24)
        p.setPen(QPen(QColor("#404040"), 1))
        p.setBrush(_LCD_BG)
        p.drawRoundedRect(panel, 3, 3)

        p.setPen(_LCD_AMBER)
        vf = QFont("Consolas"); vf.setPointSize(13); vf.setBold(True)
        p.setFont(vf)
        text = self._format() + (f" {self._spec.unit}" if self._spec.unit else "")
        p.drawText(panel, Qt.AlignCenter, text)
        p.end()


def build_gauge(spec: GaugeSpec, parent: QWidget | None = None) -> _GaugeBase:
    """Construct the gauge widget matching ``spec.style``."""
    if spec.style == STYLE_BAR:
        return BarGauge(spec, parent)
    if spec.style == STYLE_LCD:
        return LcdReadout(spec, parent)
    return DialGauge(spec, parent)
