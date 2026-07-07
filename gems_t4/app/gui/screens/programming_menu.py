"""Programming & coding sub-menu — the hub for the Phase-5 write functions.

Kept separate from the main system menu because these are the *write* operations
(gated), distinct from read-only diagnostics.
"""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen

_MENU: tuple[tuple[str, str], ...] = (
    ("Coding / settings — read, edit, write (gated)", "coding"),
    ("Immobiliser — Security-Learn re-sync", "immobiliser"),
    ("Engine maps — fuel / ignition (chip-swap)", "maps"),
)


class ProgrammingMenuScreen(Screen):
    title = "Programming & Coding"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(12)

        note = QLabel(
            "Write operations — gated. GEMS maps are NOT reflashable over the "
            "K-line (bench EPROM swap); the maps view is read-only."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 13px; color: #404040;")
        lay.addWidget(note)

        for text, target in _MENU:
            btn = QPushButton(text, objectName="MenuItem")
            btn.clicked.connect(lambda _=False, t=target: self.navigate.emit(t))
            lay.addWidget(btn)

        lay.addStretch(1)

    def nav_buttons(self) -> set[str]:
        return {"back"}
