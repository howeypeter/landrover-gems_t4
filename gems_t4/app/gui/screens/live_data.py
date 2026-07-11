"""Live-data screen — a periodically refreshed dashboard of analog gauges.

Reads $61 live measures from the backend on a :class:`QTimer` and drives a grid
of custom-painted gauges (:mod:`gems_t4.app.gui.widgets`). The refresh cadence
models the authentic T4 bandwidth character (per CLAUDE.md): watching one measure
is snappy (~20/s), but selecting every gauge drags the update rate down toward one
sample every couple of seconds. A gauge-count selector drives both how many
gauges are shown and — because more gauges means more $61 round-trips over the
slow K-line — how fast the timer ticks; the effective rate shows in the status bar.

The timer starts in :meth:`on_enter` and stops in :meth:`on_leave` (a dangling
timer would keep firing off-screen). The tick button pauses/resumes the sweep.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen
from gems_t4.app.gui.gauge_specs import spec_for
from gems_t4.app.gui.widgets import build_gauge
from gems_t4.gems.livedata import PARAMETERS

#: Selectable gauge counts: a focused few vs. the whole 37-parameter sweep.
_COUNT_CHOICES: tuple[tuple[str, int], ...] = (
    ("1 gauge", 1),
    ("4 gauges", 4),
    ("8 gauges", 8),
    ("16 gauges", 16),
    ("All gauges", 0),  # 0 == every known parameter
)
_MIN_INTERVAL_MS = 50     # ~20 Hz watching one gauge
_MAX_INTERVAL_MS = 2000   # ~1 per 2 s with the full set
_COLUMNS = 4


class LiveDataScreen(Screen):
    title = "Live Data — GEMS Engine ECU"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)
        self._all_ids: list[int] = list(PARAMETERS)
        self._paused = False
        #: local id -> gauge widget for the current selection.
        self._gauges: dict[int, object] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(QLabel("Gauges:"))
        self._count_box = QComboBox()
        for label, _n in _COUNT_CHOICES:
            self._count_box.addItem(label)
        self._count_box.setCurrentIndex(1)  # default 4 gauges
        self._count_box.currentIndexChanged.connect(self._on_count_changed)
        controls.addWidget(self._count_box)
        controls.addStretch(1)
        self._rate_label = QLabel("", objectName="Lcd")
        controls.addWidget(self._rate_label)
        lay.addLayout(controls)

        # Scrollable grid of gauges.
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self._grid = QGridLayout(self._grid_host)
        self._grid.setSpacing(8)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._scroll.setWidget(self._grid_host)
        lay.addWidget(self._scroll, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)

    # -- selection / cadence ------------------------------------------------ #
    def _selected_count(self) -> int:
        _label, n = _COUNT_CHOICES[self._count_box.currentIndex()]
        return len(self._all_ids) if n == 0 else min(n, len(self._all_ids))

    def _selected_ids(self) -> list[int]:
        return self._all_ids[: self._selected_count()]

    def _interval_ms(self) -> int:
        """Scale the timer interval with gauge count (more gauges -> slower)."""
        count = self._selected_count()
        total = len(self._all_ids)
        if total <= 1:
            return _MIN_INTERVAL_MS
        frac = (count - 1) / (total - 1)
        return round(_MIN_INTERVAL_MS + frac * (_MAX_INTERVAL_MS - _MIN_INTERVAL_MS))

    def _effective_hz(self) -> float:
        return 1000.0 / max(1, self._interval_ms())

    # -- gauge grid --------------------------------------------------------- #
    def _rebuild_gauges(self) -> None:
        """Recreate the gauge widgets for the current selection."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)   # remove from display now (deleteLater is deferred)
                w.deleteLater()
        self._gauges.clear()
        for i, lid in enumerate(self._selected_ids()):
            gauge = build_gauge(spec_for(lid))
            self._grid.addWidget(gauge, i // _COLUMNS, i % _COLUMNS)
            self._gauges[lid] = gauge
        self._refresh()

    def _refresh(self) -> None:
        """One sweep: advance the sim, read the selected measures, update gauges.

        A remote (TCP/USB) endpoint can die mid-sweep; that must stop the
        timer and report on the status bar, not raise out of a QTimer tick
        once per interval forever.
        """
        interval_s = self._interval_ms() / 1000.0
        self.backend.tick(interval_s)
        ids = self._selected_ids()
        try:
            measures = self.backend.read_live(ids)
        except Exception as exc:  # noqa: BLE001 - transport/protocol errors
            self._timer.stop()
            self._paused = True
            self._rate_label.setText("no data")
            self.status.emit(f"ECU communication error: {exc}")
            return
        for lid, m in zip(ids, measures):
            gauge = self._gauges.get(lid)
            if gauge is not None:
                gauge.set_value(m.value)

    # -- lifecycle ---------------------------------------------------------- #
    def on_enter(self) -> None:
        self._paused = False
        self._rebuild_gauges()
        self._timer.start(self._interval_ms())
        self._emit_rate()

    def on_leave(self) -> None:
        self._timer.stop()

    # -- controls ----------------------------------------------------------- #
    def _on_count_changed(self, _index: int) -> None:
        self._rebuild_gauges()
        if self._timer.isActive():
            self._timer.setInterval(self._interval_ms())
        self._emit_rate()

    def _emit_rate(self) -> None:
        count = self._selected_count()
        if self._paused:
            self._rate_label.setText("paused")
            self.status.emit(f"{count} gauge(s) - paused")
        else:
            hz = self._effective_hz()
            self._rate_label.setText(f"{hz:.1f} Hz")
            self.status.emit(f"{count} gauge(s) - refresh {hz:.1f}/s (K-line bandwidth)")

    # -- nav buttons -------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back", "tick"}

    def tick_label(self) -> str:
        return "Resume" if self._paused else "Pause"

    def on_tick(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._timer.stop()
        else:
            self._timer.start(self._interval_ms())
        self._emit_rate()
