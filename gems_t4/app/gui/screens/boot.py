"""Boot splash — the RDS 5.06 / T4 Lite start screen (the appliance-on-boot feel).

Shows the version identity and a short self-test progress sweep, then the
operator presses the tick to proceed to vehicle identification.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QLabel, QProgressBar, QVBoxLayout, QWidget

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen


class BootScreen(Screen):
    title = "TestBook T4"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(60, 40, 60, 40)
        lay.setSpacing(10)
        lay.addStretch(2)

        logo = QLabel("TESTBOOK  T4")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("font-size: 40px; font-weight: bold; letter-spacing: 3px;")
        lay.addWidget(logo)

        sub = QLabel("RDS 5.06  ·  T4 Lite")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet("font-size: 16px; color: #000080;")
        lay.addWidget(sub)

        lay.addSpacing(20)

        self._bar = QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setFixedHeight(22)
        lay.addWidget(self._bar)

        self._hint = QLabel("Starting system self-test…")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet("color: #404040;")
        lay.addWidget(self._hint)

        lay.addStretch(3)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    # -- boot animation ----------------------------------------------------- #
    def on_enter(self) -> None:
        self._bar.setValue(0)
        self._hint.setText("Starting system self-test…")
        self._timer.start(30)

    def on_leave(self) -> None:
        self._timer.stop()

    def _advance(self) -> None:
        v = min(100, self._bar.value() + 4)
        self._bar.setValue(v)
        if v >= 100:
            self._timer.stop()
            self._hint.setText("Self-test complete — press ✓ to begin")

    # -- navigation --------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"tick"}

    def on_tick(self) -> None:
        self.navigate.emit("vehicle_id")
