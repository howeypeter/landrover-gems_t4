"""The kiosk shell: a fixed 800x600 window with a title bar, a stacked content
area, and a bottom tick/cross/back button bar — plus the ``Screen`` base class
every screen subclasses.

Navigation model: screens are registered by name. A screen requests navigation by
emitting ``navigate`` with a target name; the window keeps a small history stack
so the Back button returns to the previous screen. The three global nav buttons
(tick/cross/back) delegate to the *current* screen's ``on_tick``/``on_cross``/
``on_back`` handlers, and each screen declares which buttons it wants via
``nav_buttons()``.

"The waiting": one-shot ECU operations run through ``run_with_wait`` (on both
``Screen`` and ``KioskWindow``), which shows the "Communicating with ECU"
overlay, runs the work on a background thread, and enforces the authentic
minimum display time — see :mod:`gems_t4.app.gui.wait` and CLAUDE.md design
pillar 5.
"""
from __future__ import annotations

from typing import Callable, TypeVar

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
from gems_t4.app.gui.wait import WaitController, run_inline

T = TypeVar("T")


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

    # -- "the waiting" ------------------------------------------------------- #
    def run_with_wait(
        self,
        label: str,
        fn: Callable[[], T],
        on_done: Callable[[T], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Run a backend operation behind the ECU-communication overlay.

        Delegates to the hosting :class:`KioskWindow` when there is one (the
        overlay + background worker + minimum wait). Standalone — a bare screen
        in a headless test — it falls back to running inline, so screens behave
        identically with or without the kiosk shell. Default error handling
        reports the exception on the status bar.
        """
        if on_error is None:
            on_error = lambda exc: self.status.emit(  # noqa: E731
                f"ECU communication error: {exc}"
            )
        win = self.window()
        if isinstance(win, KioskWindow):
            win.run_with_wait(label, fn, on_done, on_error)
        else:
            run_inline(fn, on_done, on_error)


class KioskWindow(QMainWindow):
    """Full-screen-feel 800x600 appliance window hosting the screens."""

    def __init__(self, backend: Backend) -> None:
        super().__init__()
        self.backend = backend
        from gems_t4 import __version__
        self.setWindowTitle(
            f"TestBook T4 — RDS 5.06 / T4 Lite — v{__version__}"
        )
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

        self._bar = self._build_button_bar()
        root.addWidget(self._bar)

        # "The waiting" — overlay + background worker over the content area.
        self._wait = WaitController(
            area=self._stack,
            set_busy=self._set_wait_busy,
            default_error=self._show_wait_error,
        )

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

    # -- "the waiting" ------------------------------------------------------- #
    def run_with_wait(
        self,
        label: str,
        fn: Callable[[], T],
        on_done: Callable[[T], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Run ``fn`` behind the "Communicating with ECU" overlay.

        Shows the overlay over the content area, disables the nav button bar,
        runs ``fn`` on a background thread, and enforces the authentic minimum
        display time before calling ``on_done(result)`` (or ``on_error(exc)``)
        back on the GUI thread. A click on the overlay skips the remaining
        minimum wait. In instant mode (``GEMS_T4_INSTANT`` set, or min-wait 0)
        the whole thing runs synchronously inline instead.
        """
        self._wait.run(label, fn, on_done, on_error)

    def _set_wait_busy(self, busy: bool) -> None:
        """Disable/enable the tick/cross/back bar while a wait is in flight."""
        self._bar.setEnabled(not busy)

    def _show_wait_error(self, exc: Exception) -> None:
        """Default error route: report the failure on the status bar."""
        self._status.setText(f"ECU communication error: {exc}")

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
