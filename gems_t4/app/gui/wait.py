""""The waiting" — the ECU-communication overlay and its background worker.

ISO 9141 is a ~10.4 kbit/s half-duplex, tester-initiated link: every real T4
exchange took visible time, and the "Communicating with ECU - please wait"
panel with its marching progress blocks is part of the tool's character (see
CLAUDE.md design pillar 5). This module recreates that in two halves:

* :class:`WaitOverlay` — a silver Win98 panel that covers the kiosk content
  area with the period wording and a busy (indeterminate) progress bar.
* :class:`WaitController` — runs the actual backend call on a background
  thread (so slow *real* hardware can never freeze the GUI) while enforcing a
  **minimum display time** so the waiting exists even against the instant
  virtual ECU. A mouse click on the overlay skips the remaining minimum wait
  (never the real work).

Escape hatch: setting the ``GEMS_T4_INSTANT`` environment variable (or
configuring :data:`DEFAULT_MIN_WAIT_MS` to 0) makes every run fully
synchronous and inline — no overlay, no thread, ``on_done`` called before
``run`` returns. Headless tests run in this mode (tests/conftest.py) so all
existing screen behaviour stays deterministic, and ``gems_t4 gui --instant``
offers it to impatient users.
"""
from __future__ import annotations

import os
from typing import Callable, TypeVar

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.gui.style import DARK_SHADOW, SILVER, SILVER_LIGHT

T = TypeVar("T")

#: Minimum time the overlay stays up, in milliseconds — the authentic waiting,
#: enforced even when the (virtual) ECU answers instantly. 0 disables the
#: overlay entirely and makes every run synchronous. Tests monkeypatch this.
DEFAULT_MIN_WAIT_MS = 900

#: Environment variable that forces synchronous/inline mode when set (non-empty).
ENV_INSTANT = "GEMS_T4_INSTANT"

#: The period-authentic headline shown on every wait (ASCII only).
HEADLINE = "Communicating with ECU - please wait"


def instant_mode() -> bool:
    """True when the waiting is disabled and runs must be synchronous."""
    return bool(os.environ.get(ENV_INSTANT))


def run_inline(
    fn: Callable[[], T],
    on_done: Callable[[T], None],
    on_error: Callable[[Exception], None] | None = None,
) -> None:
    """Run ``fn`` synchronously, routing the result/exception to the callbacks.

    The shared synchronous core used by instant mode and by screens running
    standalone (outside a KioskWindow, e.g. in headless tests). With no
    ``on_error`` the exception propagates to the caller.
    """
    try:
        result = fn()
    except Exception as exc:
        if on_error is None:
            raise
        on_error(exc)
        return
    on_done(result)


class WaitOverlay(QWidget):
    """The "Communicating with ECU" panel covering the kiosk content area.

    A transparent full-area widget (so it swallows clicks meant for the screen
    underneath) holding a centred silver Win98 panel: the headline, a smaller
    operation line ("Reading fault codes"), and an indeterminate progress bar
    for the marching-blocks feel. Clicking anywhere emits ``skip_requested``.
    """

    #: Emitted when the operator clicks the overlay to skip the remaining wait.
    skip_requested = Signal()

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.hide()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addStretch(1)

        # Silver raised panel — inline style (style.py is fixed; scoped to the
        # object name so the QLabel children don't inherit the bevel).
        panel = QFrame(self, objectName="WaitPanel")
        panel.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        panel.setStyleSheet(
            f"QFrame#WaitPanel {{ background: {SILVER};"
            f" border: 2px outset {SILVER_LIGHT}; }}"
        )
        panel.setMinimumWidth(380)

        inner = QVBoxLayout(panel)
        inner.setContentsMargins(24, 18, 24, 18)
        inner.setSpacing(10)

        headline = QLabel(HEADLINE)
        headline.setStyleSheet("font-weight: bold; background: transparent;")
        headline.setAlignment(Qt.AlignCenter)
        inner.addWidget(headline)

        self._operation = QLabel("")
        self._operation.setStyleSheet(
            f"color: {DARK_SHADOW}; font-size: 11px; background: transparent;"
        )
        self._operation.setAlignment(Qt.AlignCenter)
        inner.addWidget(self._operation)

        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # busy/indeterminate — the marching blocks
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(18)
        inner.addWidget(self._bar)

        outer.addWidget(panel, 0, Qt.AlignHCenter)
        outer.addStretch(1)

    def show_over(self, operation: str) -> None:
        """Cover the parent widget and show the panel for ``operation``."""
        self._operation.setText(operation)
        parent = self.parentWidget()
        if parent is not None:
            self.setGeometry(parent.rect())
        self.raise_()
        self.show()

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """A click anywhere on the overlay asks to skip the remaining wait."""
        self.skip_requested.emit()
        event.accept()


class _WorkerSignals(QObject):
    """Cross-thread delivery: emitted from the pool thread, queued to the GUI."""

    done = Signal(object)
    failed = Signal(object)


class _Worker(QRunnable):
    """Run one callable on the global thread pool, reporting via signals."""

    def __init__(self, fn: Callable[[], object]) -> None:
        super().__init__()
        # The controller keeps a Python reference until the run completes.
        self.setAutoDelete(False)
        self._fn = fn
        self.signals = _WorkerSignals()

    def run(self) -> None:  # pragma: no cover - exercised via the controller
        try:
            result = self._fn()
        except Exception as exc:  # noqa: BLE001 - delivered to on_error
            self.signals.failed.emit(exc)
        else:
            self.signals.done.emit(result)


class WaitController(QObject):
    """Owns one window's overlay + worker + minimum-wait timer.

    The run finishes only when BOTH the work has completed AND the minimum
    display time has elapsed (or been skipped by a click) — then the overlay
    hides, the nav bar re-enables, and exactly one of ``on_done``/``on_error``
    fires on the GUI thread. Callbacks may start a new run (chaining).
    """

    def __init__(
        self,
        area: QWidget,
        set_busy: Callable[[bool], None],
        default_error: Callable[[Exception], None],
    ) -> None:
        super().__init__(area)
        self._overlay = WaitOverlay(area)
        self._overlay.skip_requested.connect(self._skip)
        self._set_busy = set_busy
        self._default_error = default_error

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._min_elapsed)

        self._active = False
        self._min_done = False
        self._outcome: tuple[str, object] | None = None
        self._on_done: Callable[[object], None] | None = None
        self._on_error: Callable[[Exception], None] | None = None
        self._worker: _Worker | None = None

    @property
    def active(self) -> bool:
        """True while a wait is showing / work is in flight."""
        return self._active

    @property
    def overlay(self) -> WaitOverlay:
        return self._overlay

    def run(
        self,
        label: str,
        fn: Callable[[], T],
        on_done: Callable[[T], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Run ``fn`` behind the overlay (or inline in instant mode)."""
        err = on_error if on_error is not None else self._default_error
        if instant_mode() or DEFAULT_MIN_WAIT_MS <= 0:
            run_inline(fn, on_done, err)
            return
        if self._active:
            # Can't happen through the UI (the overlay blocks the screen and
            # the nav bar is disabled); a programming error otherwise.
            raise RuntimeError("an ECU-communication wait is already in progress")

        self._active = True
        self._min_done = False
        self._outcome = None
        self._on_done = on_done
        self._on_error = err

        self._set_busy(True)
        self._overlay.show_over(label)
        self._timer.start(int(DEFAULT_MIN_WAIT_MS))

        worker = _Worker(fn)
        worker.signals.done.connect(self._work_done)
        worker.signals.failed.connect(self._work_failed)
        self._worker = worker
        QThreadPool.globalInstance().start(worker)

    # -- completion plumbing (all on the GUI thread) ------------------------- #
    def _work_done(self, result: object) -> None:
        if self._active:
            self._outcome = ("done", result)
            self._maybe_finish()

    def _work_failed(self, exc: object) -> None:
        if self._active:
            self._outcome = ("error", exc)
            self._maybe_finish()

    def _min_elapsed(self) -> None:
        self._min_done = True
        self._maybe_finish()

    def _skip(self) -> None:
        """Skip the remaining minimum wait (the work itself is never skipped)."""
        if self._active:
            self._timer.stop()
            self._min_done = True
            self._maybe_finish()

    def _maybe_finish(self) -> None:
        if not self._active or self._outcome is None or not self._min_done:
            return
        kind, payload = self._outcome
        on_done, on_error = self._on_done, self._on_error
        # Clear state BEFORE dispatching so a callback may chain a new run.
        self._active = False
        self._outcome = None
        self._on_done = None
        self._on_error = None
        self._worker = None
        self._timer.stop()
        self._overlay.hide()
        self._set_busy(False)
        if kind == "error":
            assert on_error is not None
            on_error(payload)  # type: ignore[arg-type]
        else:
            assert on_done is not None
            on_done(payload)
