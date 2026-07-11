"""System / function selection — the hub screen the other functions hang off.

VIN-first design: by the time we reach here the vehicle is identified, so this
lists the fitted systems' functions. For v1 that is the GEMS engine ECU's
fault codes, live data, actuator tests, and the toolbox self-tests.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen

#: (button text, target screen name)
_MENU: tuple[tuple[str, str], ...] = (
    ("Fault codes — read / clear", "fault_codes"),
    ("Live data — sensor values", "live_data"),
    ("Actuator tests — output drives", "actuators"),
    ("Programming & coding — write functions", "programming_menu"),
    ("Toolbox — self-tests & about", "toolbox"),
    ("Configuration — VCI connection", "connection"),
)


class SystemMenuScreen(Screen):
    title = "Select Function — GEMS Engine ECU"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(12)

        self._header = QLabel()
        self._header.setStyleSheet("font-size: 13px; color: #404040;")
        lay.addWidget(self._header)

        for text, target in _MENU:
            btn = QPushButton(text, objectName="MenuItem")
            btn.clicked.connect(lambda _=False, t=target: self.navigate.emit(t))
            lay.addWidget(btn)

        lay.addStretch(1)

    def on_enter(self) -> None:
        if self.backend.is_remote:
            # connection_label already carries read-only/writes-enabled mode.
            self._header.setText(
                f"Lucas/SAGEM GEMS 8 · {self.backend.connection_label}"
            )
        else:
            self._header.setText(
                f"Lucas/SAGEM GEMS 8 · simulated scenario: "
                f"{self.backend.scenario_name}"
            )

    def nav_buttons(self) -> set[str]:
        return {"back"}
