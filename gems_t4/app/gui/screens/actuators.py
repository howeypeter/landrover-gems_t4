"""Actuator-tests screen — command the GEMS output drives on and off.

Each fitted actuator gets a row: its name plus a "Test On"/"Test Off" pair of
buttons. Running one calls ``backend.run_actuator(id, state)`` and shows the
returned :class:`~gems_t4.gems.types.ActuatorOutcome` in a prominent amber
LCD-style readout — success in green, refusal in red.

The characterful moment: the **fuel pump relay is refused while the engine is
running** (``allowed_engine_running=False``), so its outcome comes back
``ok=False`` with a "conditions not correct" message. Refusals are rendered
distinctly (red text) from successes (green) so the technician can't miss it —
the authentic T4 "Test not available — engine running" behaviour.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen
from gems_t4.app.gui.style import GREEN_OK, LCD_AMBER, RED_BAD
from gems_t4.gems.actuators import ActuatorOutcome, STATE_OFF, STATE_ON


class ActuatorsScreen(Screen):
    """List the GEMS actuator outputs and drive each on/off, showing outcomes."""

    title = "Actuator Tests"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        caption = QLabel("Output / actuator tests — command a drive on or off")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(0, 1)
        lay.addLayout(grid)

        for row, act in enumerate(self.backend.actuator_list()):
            name = QLabel(act.name)
            grid.addWidget(name, row, 0)

            on_btn = QPushButton("Test On")
            on_btn.clicked.connect(
                lambda _=False, a=act.actuator_id: self._run(a, STATE_ON)
            )
            grid.addWidget(on_btn, row, 1)

            off_btn = QPushButton("Test Off")
            off_btn.clicked.connect(
                lambda _=False, a=act.actuator_id: self._run(a, STATE_OFF)
            )
            grid.addWidget(off_btn, row, 2)

        lay.addStretch(1)

        self._readout = QLabel("Select an actuator to test.", objectName="Lcd")
        self._readout.setWordWrap(True)
        self._readout.setMinimumHeight(40)
        lay.addWidget(self._readout)

    # -- lifecycle ---------------------------------------------------------- #
    def on_enter(self) -> None:
        """Reset the readout each time the screen is shown."""
        self._readout.setStyleSheet(f"color: {LCD_AMBER};")
        self._readout.setText("Select an actuator to test.")
        self.status.emit("Ready — select an actuator output to drive.")

    # -- running ------------------------------------------------------------ #
    def _run(self, actuator_id: int, state: int) -> None:
        """Command an actuator test and display its outcome distinctly."""
        outcome: ActuatorOutcome = self.backend.run_actuator(actuator_id, state)
        self._show_outcome(outcome)

    def _show_outcome(self, outcome: ActuatorOutcome) -> None:
        """Render an outcome: green for success, red for a refusal."""
        colour = GREEN_OK if outcome.ok else RED_BAD
        prefix = "OK" if outcome.ok else "REFUSED"
        self._readout.setStyleSheet(f"color: {colour}; font-weight: bold;")
        self._readout.setText(f"{prefix}: {outcome.message}")
        self.status.emit(outcome.message)

    # -- nav buttons -------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back"}
