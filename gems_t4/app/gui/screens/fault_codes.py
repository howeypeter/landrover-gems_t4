"""Fault-codes screen — read and clear stored DTCs.

This is the reference screen for how a screen talks to the backend: ``on_enter``
reads via ``backend.read_dtcs()`` and fills a table; the tick re-reads; the cross
clears (with a two-step inline confirmation — no blocking modal dialog, which
keeps the kiosk flow and the headless tests simple).

Reads and clears go through ``run_with_wait`` — the "Communicating with ECU"
overlay — because pulling codes over the half-duplex K-line took visible time
on the real tool (CLAUDE.md design pillar 5). In instant mode this degrades to
the old synchronous behaviour.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen
from gems_t4.gems.types import Dtc


class FaultCodesScreen(Screen):
    title = "Fault Codes"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)
        self._pending_clear = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)

        caption = QLabel("Stored diagnostic trouble codes")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Code", "State", "Description"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 80)
        self._table.setColumnWidth(1, 90)
        lay.addWidget(self._table, 1)

        self._hint = QLabel("✓ Read codes     ✗ Clear codes")
        self._hint.setStyleSheet("color: #404040;")
        lay.addWidget(self._hint)

    # -- data --------------------------------------------------------------- #
    def on_enter(self) -> None:
        self._pending_clear = False
        self._read()

    def _read(self) -> None:
        """Read the stored codes behind the ECU-communication wait."""
        self._pending_clear = False
        self.run_with_wait("Reading fault codes", self.backend.read_dtcs, self._show)

    def _show(self, dtcs: list[Dtc]) -> None:
        """Fill the table from a freshly read DTC list (GUI thread)."""
        self._table.setRowCount(len(dtcs))
        for row, d in enumerate(dtcs):
            self._table.setItem(row, 0, QTableWidgetItem(d.code))
            self._table.setItem(row, 1, QTableWidgetItem(d.state.value))
            self._table.setItem(row, 2, QTableWidgetItem(d.description))
        if dtcs:
            self.status.emit(f"{len(dtcs)} fault code(s) stored")
            self._hint.setText("✓ Read codes     ✗ Clear codes")
        else:
            self.status.emit("No fault codes stored")
            self._hint.setText("No faults · ✓ Read again")

    def _clear(self) -> None:
        if not self._pending_clear:
            self._pending_clear = True
            self.status.emit("Clear all stored codes? Press ✗ again to confirm.")
            self._hint.setText("⚠ Press ✗ again to confirm clear")
            return
        self._pending_clear = False

        def work() -> list[Dtc]:
            self.backend.clear_dtcs()
            return self.backend.read_dtcs()  # re-read to confirm the clear

        self.run_with_wait("Clearing fault codes", work, self._show)

    # -- nav buttons -------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back", "cross", "tick"}

    def on_tick(self) -> None:
        self._read()

    def on_cross(self) -> None:
        self._clear()
