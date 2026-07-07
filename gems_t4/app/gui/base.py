"""The kiosk shell: a fixed 800x600 window with a title bar, a stacked content
area, and a bottom tick/cross/back button bar — plus the ``Screen`` base class
every screen subclasses.

Navigation model: screens are registered by name. A screen requests navigation by
emitting ``navigate`` with a target name; the window keeps a small history stack
so the Back button returns to the previous screen. The three global nav buttons
(tick/cross/back) delegate to the *current* screen's ``on_tick``/``on_cross``/
``on_back`` handlers, and each screen declares which buttons it wants via
``nav_buttons()``.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.style import SCREEN_H, SCREEN_W, WIN98_QSS


class Screen(QWidget):
    """Base class for a kiosk screen.

    Subclasses set :attr:`title`, build their UI in ``__init__``, and may override
    :meth:`on_enter` (refresh from the backend when shown), :meth:`on_leave`, and
    the nav handlers. Request navigation with ``self.navigate.emit("<name>")``.
    """

    #: Emitted to ask the window to switch to the named screen.
    navigate = Signal(str)
    #: Emitted to update the status-bar text (optional).
    status = Signal(str)

    #: Human-readable title shown in the window title bar.
    title: str = "Screen"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend = backend

    # -- lifecycle hooks (overridable) ------------------------------------- #
    def on_enter(self) -> None:
        """Called each time this screen becomes visible."""

    def on_leave(self) -> None:
        """Called when navigating away from this screen."""

    # -- nav-button wiring (overridable) ----------------------------------- #
    def nav_buttons(self) -> set[str]:
        """Which of ``{"back", "cross", "tick"}`` to show. Default: just back."""
        return {"back"}

    def tick_label(self) -> str:
        return "✓"  # ✓

    def cross_label(self) -> str:
        return "✗"  # ✗

    def on_tick(self) -> None:
        """Handle the global tick (OK/confirm) button."""

    def on_cross(self) -> None:
        """Handle the global cross (cancel/no) button."""

    def on_back(self) -> bool:
        """Handle Back. Return True if handled; False to let the window pop history."""
        return False


class KioskWindow(QMainWindow):
    """Full-screen-feel 800x600 appliance window hosting the screens."""

    def __init__(self, backend: Backend) -> None:
        super().__init__()
        self.backend = backend
        self.setWindowTitle("TestBook T4 — RDS 5.06 / T4 Lite")
        self.setFixedSize(SCREEN_W, SCREEN_H)
        self.setStyleSheet(WIN98_QSS)

        self._screens: dict[str, Screen] = {}
        self._history: list[str] = []

        central = QWidget(objectName="Kiosk")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._title = QLabel("TestBook T4", objectName="TitleBar")
        root.addWidget(self._title)

        self._stack = QStackedWidget(objectName="Content")
        root.addWidget(self._stack, 1)

        self._status = QLabel("", objectName="StatusBar")
        root.addWidget(self._status)

        root.addWidget(self._build_button_bar())

    # -- button bar --------------------------------------------------------- #
    def _build_button_bar(self) -> QFrame:
        bar = QFrame(objectName="ButtonBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 6, 8, 6)

        self._btn_back = QPushButton("← Back", objectName="NavBack")
        self._btn_back.clicked.connect(self._on_back_clicked)
        lay.addWidget(self._btn_back)

        lay.addStretch(1)

        self._btn_cross = QPushButton("✗", objectName="NavCross")
        self._btn_cross.clicked.connect(lambda: self._delegate("on_cross"))
        lay.addWidget(self._btn_cross)

        self._btn_tick = QPushButton("✓", objectName="NavTick")
        self._btn_tick.clicked.connect(lambda: self._delegate("on_tick"))
        lay.addWidget(self._btn_tick)

        return bar

    # -- registration / navigation ----------------------------------------- #
    def register(self, name: str, screen: Screen) -> None:
        self._screens[name] = screen
        self._stack.addWidget(screen)
        screen.navigate.connect(self.go)
        screen.status.connect(self._status.setText)

    def go(self, name: str) -> None:
        """Navigate to a screen, pushing the current one onto the history stack."""
        if name not in self._screens:
            raise KeyError(f"unknown screen {name!r}")
        current = self.current_name()
        if current is not None and current != name:
            self._history.append(current)
        self._show(name)

    def _show(self, name: str) -> None:
        prev = self._current_screen()
        if prev is not None:
            prev.on_leave()
        screen = self._screens[name]
        self._stack.setCurrentWidget(screen)
        self._title.setText(screen.title)
        self._apply_nav_buttons(screen)
        self._status.setText("")
        screen.on_enter()

    def back(self) -> None:
        """Pop the history stack and show the previous screen."""
        if self._history:
            self._show(self._history.pop())

    def current_name(self) -> str | None:
        w = self._stack.currentWidget()
        for name, screen in self._screens.items():
            if screen is w:
                return name
        return None

    def _current_screen(self) -> Screen | None:
        w = self._stack.currentWidget()
        return w if isinstance(w, Screen) else None

    # -- button delegation -------------------------------------------------- #
    def _apply_nav_buttons(self, screen: Screen) -> None:
        wanted = screen.nav_buttons()
        self._btn_back.setVisible("back" in wanted)
        self._btn_cross.setVisible("cross" in wanted)
        self._btn_tick.setVisible("tick" in wanted)
        self._btn_tick.setText(screen.tick_label())
        self._btn_cross.setText(screen.cross_label())
        self._btn_back.setEnabled(bool(self._history))

    def _delegate(self, method: str) -> None:
        screen = self._current_screen()
        if screen is not None:
            getattr(screen, method)()

    def _on_back_clicked(self) -> None:
        screen = self._current_screen()
        if screen is not None and screen.on_back():
            return
        self.back()
