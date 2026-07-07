"""Immobiliser / Security-Learn screen — show status and re-sync the ECU.

This is the P38's canon "ENGINE IMMOBILISED" failure and the ONE genuine GEMS
over-the-wire write. The GEMS ECM won't run until the BeCM sends a coded
mobilisation signal; if the two fall out of sync you get the non-start, and the
Security-Learn procedure ($27 access → $31 learn routines) re-syncs them.

The screen:

* On ``on_enter`` reads ``backend.immobiliser_status()`` and shows ``.summary``
  in an LCD-style readout — green for MOBILISED, red for ENGINE IMMOBILISED.
* "Simulate ENGINE IMMOBILISED" forces the failure mode so a technician can demo
  it, then refreshes the status.
* "Run Security-Learn" runs ``backend.security_learn(on_progress=...)``,
  streaming each step live into the log area, then shows the
  :class:`~gems_t4.gems.immobiliser.SecurityLearnResult` and refreshes the
  status (which should become MOBILISED on success).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen
from gems_t4.app.gui.style import GREEN_OK, LCD_AMBER, RED_BAD
from gems_t4.gems.immobiliser import ImmobiliserStatus, SecurityLearnResult


class ImmobiliserScreen(Screen):
    """Show immobiliser status and run the Security-Learn re-sync."""

    title = "Immobiliser — Security-Learn"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        caption = QLabel("Engine immobiliser status — BeCM/ECM mobilisation sync")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        #: Prominent LCD readout of the current immobiliser summary.
        self._readout = QLabel("Reading immobiliser status…", objectName="Lcd")
        self._readout.setWordWrap(True)
        self._readout.setMinimumHeight(48)
        lay.addWidget(self._readout)

        # -- action buttons ------------------------------------------------- #
        buttons = QHBoxLayout()
        buttons.setSpacing(8)

        self._btn_simulate = QPushButton("Simulate ENGINE IMMOBILISED")
        self._btn_simulate.clicked.connect(self._simulate_immobilised)
        buttons.addWidget(self._btn_simulate)

        self._btn_learn = QPushButton("Run Security-Learn")
        self._btn_learn.clicked.connect(self._run_security_learn)
        buttons.addWidget(self._btn_learn)

        buttons.addStretch(1)
        lay.addLayout(buttons)

        log_caption = QLabel("Security-Learn steps")
        log_caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(log_caption)

        #: Live step log — each Security-Learn step is appended here.
        self._log = QListWidget()
        lay.addWidget(self._log, 1)

    # -- lifecycle ---------------------------------------------------------- #
    def on_enter(self) -> None:
        """Refresh the immobiliser status each time the screen is shown."""
        self._refresh_status()

    # -- status ------------------------------------------------------------- #
    def _refresh_status(self) -> None:
        """Read the immobiliser status and render it in the LCD readout."""
        status: ImmobiliserStatus = self.backend.immobiliser_status()
        self._show_status(status)

    def _show_status(self, status: ImmobiliserStatus) -> None:
        """Render a status: green when mobilised, red when immobilised."""
        colour = GREEN_OK if status.mobilised else RED_BAD
        self._readout.setStyleSheet(f"color: {colour}; font-weight: bold;")
        self._readout.setText(status.summary)
        self.status.emit(status.summary)

    # -- actions ------------------------------------------------------------ #
    def _simulate_immobilised(self) -> None:
        """Force the ENGINE IMMOBILISED failure mode, then refresh."""
        self.backend.set_immobilised(True)
        self._log.clear()
        self._refresh_status()

    def _run_security_learn(self) -> None:
        """Run Security-Learn, streaming each step live into the log."""
        self._log.clear()
        self._readout.setStyleSheet(f"color: {LCD_AMBER}; font-weight: bold;")
        self._readout.setText("SECURITY-LEARN IN PROGRESS…")
        self.status.emit("Running Security-Learn…")

        result: SecurityLearnResult = self.backend.security_learn(
            on_progress=self._on_step
        )

        prefix = "OK" if result.ok else "FAILED"
        self._log.addItem(f"{prefix}: {result.message}")
        # Refresh the status — should read MOBILISED on success.
        self._refresh_status()

    def _on_step(self, message: str) -> None:
        """Progress callback: append one Security-Learn step to the log."""
        self._log.addItem(message)

    # -- nav buttons -------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back"}
