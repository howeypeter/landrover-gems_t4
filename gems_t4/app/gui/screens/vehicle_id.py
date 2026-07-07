"""Vehicle identification screen — VIN-first identity + fault-scenario selection.

This is the guided first fork of every P38 procedure ("GEMS or Thor?"). The
operator enters/confirms a VIN, sees the vehicle it decodes to, and — crucially —
picks which fault *scenario* the virtual ECU should present. That choice is the
vehicle-configuration step: it decides what the downstream fault-code, live-data,
and actuator screens will show, so it lives here and is committed on the tick.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen

#: A plausible P38 Range Rover VIN (SALLPAM…-style Solihull 17-char) to prefill.
_DEFAULT_VIN = "SALLPAMJ3WA123456"

#: The vehicle the VIN above decodes to — the GEMS fork, per CLAUDE.md.
_VEHICLE_SUMMARY = "Range Rover P38 · 4.0/4.6 V8 · Lucas/SAGEM GEMS (1995–99)"


class VehicleIdScreen(Screen):
    """VIN-first vehicle identification and fault-scenario selection."""

    title = "Vehicle Identification"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(14)

        caption = QLabel("Identify the vehicle to configure the diagnostic session")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self._vin = QLineEdit(_DEFAULT_VIN)
        self._vin.setMaxLength(17)
        self._vin.setToolTip("Vehicle Identification Number (17 characters)")
        form.addRow("VIN:", self._vin)

        self._summary = QLabel(_VEHICLE_SUMMARY)
        self._summary.setObjectName("Lcd")
        self._summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Identified:", self._summary)

        #: The vehicle-config choice: which fault scenario the ECU presents.
        self._scenario = QComboBox()
        for name in self.backend.available_scenarios():
            self._scenario.addItem(name)
        form.addRow("Test scenario:", self._scenario)

        lay.addLayout(form)

        note = QLabel(
            "The selected scenario configures the fitted-system responses for "
            "fault codes, live data and actuator tests. Press ✓ to confirm."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #404040;")
        lay.addWidget(note)

        lay.addStretch(1)

    # -- data --------------------------------------------------------------- #
    def on_enter(self) -> None:
        """Sync the combo to the backend's current scenario and prompt the user."""
        current = self.backend.scenario_name
        idx = self._scenario.findText(current)
        if idx >= 0:
            self._scenario.setCurrentIndex(idx)
        self.status.emit("Confirm VIN and test scenario, then press ✓ to continue.")

    # -- navigation --------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back", "tick"}

    def on_tick(self) -> None:
        """Commit the chosen scenario, then advance to the system menu."""
        chosen = self._scenario.currentText()
        self.backend.set_scenario(chosen)
        self.status.emit(f"Vehicle configured · scenario: {chosen}")
        self.navigate.emit("system_menu")
