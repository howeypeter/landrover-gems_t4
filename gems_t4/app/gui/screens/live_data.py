"""Live-data screen — a periodically refreshed sensor dashboard.

Reads $61 live measures from the backend on a :class:`QTimer` and updates a
table in place. The refresh cadence deliberately models the authentic T4
bandwidth character (per CLAUDE.md): watching one measure is snappy (~20/s),
but selecting every gauge drags the update rate down toward one sample every
couple of seconds. A parameter-count selector drives both how many rows are
shown and — because more gauges means more $61 round-trips over the slow
K-line — how fast the timer ticks. The effective rate is surfaced in the
status bar.

Lifecycle: the timer starts in :meth:`on_enter` and is stopped in
:meth:`on_leave` (a dangling timer would keep firing after navigation and
interfere with other screens/tests). The tick button pauses/resumes the sweep.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen
from gems_t4.gems.livedata import PARAMETERS

#: Selectable gauge counts: a focused few vs. the whole ~24-parameter sweep.
#: (label, number of parameters to show).
_COUNT_CHOICES: tuple[tuple[str, int], ...] = (
    ("1 gauge", 1),
    ("4 gauges", 4),
    ("8 gauges", 8),
    ("16 gauges", 16),
    ("All gauges", 0),  # 0 == every known parameter
)

#: The interval, in milliseconds, that one gauge refreshes at (~20 samples/s).
_MIN_INTERVAL_MS = 50
#: The interval, in milliseconds, with the full gauge set (~1 per 2 s).
_MAX_INTERVAL_MS = 2000


class LiveDataScreen(Screen):
    """Live sensor dashboard with a gauge-count → refresh-rate trade-off."""

    title = "Live Data — GEMS Engine ECU"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        #: All known live-data local ids, in definition order.
        self._all_ids: list[int] = list(PARAMETERS)
        self._paused = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)

        # -- top control row: gauge-count selector -------------------------- #
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(QLabel("Gauges:"))

        self._count_box = QComboBox()
        for label, _n in _COUNT_CHOICES:
            self._count_box.addItem(label)
        self._count_box.setCurrentIndex(1)  # default to 4 gauges
        self._count_box.currentIndexChanged.connect(self._on_count_changed)
        controls.addWidget(self._count_box)
        controls.addStretch(1)

        self._rate_label = QLabel("", objectName="Lcd")
        controls.addWidget(self._rate_label)
        lay.addLayout(controls)

        # -- the live table (updated in place) ------------------------------ #
        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Parameter", "Value", "Unit"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 260)
        self._table.setColumnWidth(1, 120)
        lay.addWidget(self._table, 1)

        # -- refresh timer (started in on_enter) ---------------------------- #
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)

    # -- selected ids / cadence -------------------------------------------- #
    def _selected_count(self) -> int:
        """How many parameters the current selection asks for (0 → all)."""
        _label, n = _COUNT_CHOICES[self._count_box.currentIndex()]
        return len(self._all_ids) if n == 0 else min(n, len(self._all_ids))

    def _selected_ids(self) -> list[int]:
        return self._all_ids[: self._selected_count()]

    def _interval_ms(self) -> int:
        """Scale the timer interval with gauge count (more gauges → slower).

        Linear interpolation between the one-gauge and all-gauges endpoints so
        the update rate visibly degrades as parameters are added — the
        authentic K-line bandwidth trade-off.
        """
        count = self._selected_count()
        total = len(self._all_ids)
        if total <= 1:
            return _MIN_INTERVAL_MS
        frac = (count - 1) / (total - 1)
        return round(_MIN_INTERVAL_MS + frac * (_MAX_INTERVAL_MS - _MIN_INTERVAL_MS))

    def _effective_hz(self) -> float:
        return 1000.0 / max(1, self._interval_ms())

    # -- table population --------------------------------------------------- #
    def _rebuild_rows(self) -> None:
        """Resize the table to the selected count and label each row once.

        Row labels are set here; only the value/unit cells change each tick,
        so :meth:`_refresh` can update text in place rather than rebuilding.
        """
        ids = self._selected_ids()
        self._table.setRowCount(len(ids))
        measures = self.backend.read_live(ids)
        for row, m in enumerate(measures):
            self._table.setItem(row, 0, QTableWidgetItem(m.name))
            self._table.setItem(row, 1, QTableWidgetItem(m.formatted()))
            self._table.setItem(row, 2, QTableWidgetItem(m.unit))

    def _refresh(self) -> None:
        """One sweep: advance the sim, read the selected measures, update cells."""
        interval_s = self._interval_ms() / 1000.0
        self.backend.tick(interval_s)
        measures = self.backend.read_live(self._selected_ids())

        # keep the row count in sync if the selection changed under us
        if self._table.rowCount() != len(measures):
            self._table.setRowCount(len(measures))

        for row, m in enumerate(measures):
            name_item = self._table.item(row, 0)
            if name_item is None:
                self._table.setItem(row, 0, QTableWidgetItem(m.name))
            else:
                name_item.setText(m.name)

            value_item = self._table.item(row, 1)
            if value_item is None:
                value_item = QTableWidgetItem()
                self._table.setItem(row, 1, value_item)
            value_item.setText(m.formatted())

            unit_item = self._table.item(row, 2)
            if unit_item is None:
                self._table.setItem(row, 2, QTableWidgetItem(m.unit))
            else:
                unit_item.setText(m.unit)

    # -- lifecycle ---------------------------------------------------------- #
    def on_enter(self) -> None:
        """Populate immediately and start the refresh timer."""
        self._paused = False
        self._rebuild_rows()
        self._timer.start(self._interval_ms())
        self._emit_rate()

    def on_leave(self) -> None:
        """Stop the timer so it does not keep firing off-screen (critical)."""
        self._timer.stop()

    # -- controls ----------------------------------------------------------- #
    def _on_count_changed(self, _index: int) -> None:
        """React to a new gauge-count selection: rebuild rows, re-cadence."""
        self._rebuild_rows()
        if self._timer.isActive():
            self._timer.setInterval(self._interval_ms())
        self._emit_rate()

    def _emit_rate(self) -> None:
        count = self._selected_count()
        if self._paused:
            self.status.emit(f"Paused · {count} gauge(s) selected")
            return
        self.status.emit(
            f"{count} gauge(s) · refresh {self._effective_hz():.1f} Hz "
            f"(more gauges = slower, over the K-line)"
        )
        self._rate_label.setText(f"{self._effective_hz():.1f} Hz")

    # -- nav buttons -------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back", "tick"}

    def tick_label(self) -> str:
        return "❚❚" if not self._paused else "▶"

    def on_tick(self) -> None:
        """Pause/resume the live sweep."""
        self._paused = not self._paused
        if self._paused:
            self._timer.stop()
        else:
            self._timer.start(self._interval_ms())
        self._emit_rate()
