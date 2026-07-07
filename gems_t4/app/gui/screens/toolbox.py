"""Toolbox screen — operator self-tests and About (the Rover "party pieces").

The real RDS Toolbox let a technician run appliance self-checks (LAN card, VCI,
touchscreen calibration) and read the tool identity. We reproduce those as a
list of selectable checks, each writing its result into an LCD-style readout —
quoting the canonical period messages verbatim for authenticity.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen

#: The canon LAN-card disclaimer, quoted verbatim from CLAUDE.md — do not edit.
_LAN_DISCLAIMER = (
    "The LAN facility is intended for potential future developments in "
    "dealership systems, and is not currently in use."
)

#: Tool identity reported on boot and in About (per CLAUDE.md spec).
_ABOUT_IDENTITY = "RDS 5.06 / T4 Lite"


class ToolboxScreen(Screen):
    """Self-tests and About readout — data/text only, no diagnostics traffic."""

    title = "Toolbox — Self-Tests & About"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        #: Each check maps a label to a function returning its readout text.
        self._checks: dict[str, Callable[[], str]] = {
            "LAN card check": self._lan_card_check,
            "VCI check": self._vci_check,
            "Touchscreen calibration": self._touchscreen_check,
            "About": self._about,
        }

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(10)

        caption = QLabel("Select a self-test or About to run it")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        body = QHBoxLayout()
        body.setSpacing(14)

        self._list = QListWidget()
        for name in self._checks:
            self._list.addItem(QListWidgetItem(name))
        self._list.currentTextChanged.connect(self._run_check)
        self._list.setMaximumWidth(240)
        body.addWidget(self._list)

        self._readout = QLabel("")
        self._readout.setObjectName("Lcd")
        self._readout.setWordWrap(True)
        self._readout.setMinimumHeight(180)
        self._readout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        body.addWidget(self._readout, 1)

        lay.addLayout(body, 1)

    # -- lifecycle ---------------------------------------------------------- #
    def on_enter(self) -> None:
        """Preselect the first check so the readout is never blank."""
        if self._list.currentRow() < 0:
            self._list.setCurrentRow(0)
        else:
            self._run_check(self._list.currentItem().text())
        self.status.emit("Toolbox — appliance self-tests and About.")

    # -- check runner ------------------------------------------------------- #
    def _run_check(self, name: str) -> None:
        """Run the selected check and write its result into the readout panel."""
        if not name:
            return
        runner = self._checks.get(name)
        if runner is None:
            return
        self._readout.setText(runner())
        self.status.emit(f"{name} complete.")

    # -- individual self-tests --------------------------------------------- #
    def _lan_card_check(self) -> str:
        """LAN card presence check — quotes the canon dealership disclaimer."""
        return "LAN card: present\n\n" + _LAN_DISCLAIMER

    def _vci_check(self) -> str:
        """Vehicle Communication Interface presence/response check."""
        return (
            "VCI: present / responding\n\n"
            "VCSI interface box detected on the LAN unit; J1962 lead ready."
        )

    def _touchscreen_check(self) -> str:
        """Touchscreen calibration stub result."""
        return (
            "Touchscreen calibration: OK\n\n"
            "Alignment within tolerance — no re-calibration required."
        )

    def _about(self) -> str:
        """Tool identity / About readout."""
        return (
            f"{_ABOUT_IDENTITY}\n\n"
            "TestBook T4 Mobile — Rover / Land Rover dealer diagnostics\n"
            "Built by Omitec · RDS operating environment"
        )

    # -- navigation --------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back"}
