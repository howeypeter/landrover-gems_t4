""""The waiting" (gems_t4/app/gui/wait.py): instant mode, worker, skip, errors.

Headless (tests/conftest.py forces the offscreen Qt platform AND sets
``GEMS_T4_INSTANT=1`` so all other GUI tests run the waits synchronously).
The async-path tests here unset the env var via monkeypatch and shrink the
minimum wait so the real overlay + background worker are exercised quickly.
Requires the ``gui`` extra; skips cleanly if PySide6 is not installed.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt

from gems_t4.app.backend import Backend
from gems_t4.app.gui import wait as wait_mod
from gems_t4.app.gui.base import KioskWindow, Screen


def _boom() -> None:
    raise RuntimeError("no response from ECU")


@pytest.fixture
def window(qtbot) -> KioskWindow:
    win = KioskWindow(Backend("healthy"))
    qtbot.addWidget(win)
    return win


# --------------------------------------------------------------------------- #
# Instant / synchronous mode (the escape hatch; conftest sets GEMS_T4_INSTANT)
# --------------------------------------------------------------------------- #
def test_instant_mode_runs_synchronously(window: KioskWindow) -> None:
    """With GEMS_T4_INSTANT set, on_done fires before run_with_wait returns."""
    got: list[int] = []
    window.run_with_wait("op", lambda: 42, got.append)
    assert got == [42]
    assert not window._wait.active
    assert not window._wait.overlay.isVisible()
    assert window._bar.isEnabled()


def test_instant_mode_error_routes_to_on_error(window: KioskWindow) -> None:
    """A raising fn calls on_error with the exception; on_done never fires."""
    errors: list[Exception] = []
    window.run_with_wait(
        "op",
        _boom,
        on_done=lambda _r: pytest.fail("on_done must not fire on error"),
        on_error=errors.append,
    )
    assert len(errors) == 1
    assert "no response from ECU" in str(errors[0])


def test_instant_mode_default_error_goes_to_status_bar(window: KioskWindow) -> None:
    """With no on_error, the failure is reported on the window status bar."""
    window.run_with_wait(
        "op", _boom, on_done=lambda _r: pytest.fail("on_done must not fire")
    )
    assert "no response from ECU" in window._status.text()


def test_zero_min_wait_is_synchronous_without_env(window, monkeypatch) -> None:
    """Min-wait configured to 0 is the other instant switch (no env var)."""
    monkeypatch.delenv(wait_mod.ENV_INSTANT, raising=False)
    monkeypatch.setattr(wait_mod, "DEFAULT_MIN_WAIT_MS", 0)
    got: list[int] = []
    window.run_with_wait("op", lambda: 1, got.append)
    assert got == [1]


# --------------------------------------------------------------------------- #
# The real async path: overlay + background worker + minimum wait
# --------------------------------------------------------------------------- #
def test_async_path_shows_overlay_then_completes(qtbot, window, monkeypatch) -> None:
    """Async: overlay up + nav bar disabled while waiting, then on_done fires,
    the overlay hides and the bar re-enables."""
    monkeypatch.delenv(wait_mod.ENV_INSTANT, raising=False)
    monkeypatch.setattr(wait_mod, "DEFAULT_MIN_WAIT_MS", 30)
    window.show()

    got: list[str] = []
    window.run_with_wait("Reading fault codes", lambda: "ok", got.append)

    # Immediately after the call: waiting, blocked, nothing delivered yet
    # (the minimum wait has not elapsed and no event loop has run).
    assert window._wait.active
    assert window._wait.overlay.isVisible()
    assert not window._bar.isEnabled()
    assert got == []

    qtbot.waitUntil(lambda: got == ["ok"], timeout=2000)
    assert not window._wait.active
    assert not window._wait.overlay.isVisible()
    assert window._bar.isEnabled()


def test_async_error_routes_to_on_error(qtbot, window, monkeypatch) -> None:
    """Async: a raising fn still lands in on_error on the GUI thread."""
    monkeypatch.delenv(wait_mod.ENV_INSTANT, raising=False)
    monkeypatch.setattr(wait_mod, "DEFAULT_MIN_WAIT_MS", 10)
    window.show()

    errors: list[Exception] = []
    window.run_with_wait(
        "op",
        _boom,
        on_done=lambda _r: pytest.fail("on_done must not fire on error"),
        on_error=errors.append,
    )
    qtbot.waitUntil(lambda: len(errors) == 1, timeout=2000)
    assert "no response from ECU" in str(errors[0])
    assert not window._wait.overlay.isVisible()
    assert window._bar.isEnabled()


def test_click_skips_remaining_minimum_wait(qtbot, window, monkeypatch) -> None:
    """A click on the overlay skips the (long) remaining minimum wait — the
    result arrives well before the 5 s minimum would have elapsed."""
    monkeypatch.delenv(wait_mod.ENV_INSTANT, raising=False)
    monkeypatch.setattr(wait_mod, "DEFAULT_MIN_WAIT_MS", 5000)
    window.show()

    got: list[str] = []
    window.run_with_wait("op", lambda: "done", got.append)
    assert window._wait.overlay.isVisible()

    qtbot.mouseClick(window._wait.overlay, Qt.LeftButton)

    # Without the skip this would need ~5 s; the 2 s timeout proves the skip.
    qtbot.waitUntil(lambda: got == ["done"], timeout=2000)
    assert not window._wait.overlay.isVisible()
    assert window._bar.isEnabled()


# --------------------------------------------------------------------------- #
# Screen-level fallback (standalone screens, as in the headless screen tests)
# --------------------------------------------------------------------------- #
def test_screen_standalone_runs_inline(qtbot) -> None:
    """A screen outside a KioskWindow falls back to synchronous inline runs."""
    screen = Screen(Backend("healthy"))
    qtbot.addWidget(screen)
    got: list[int] = []
    screen.run_with_wait("op", lambda: 7, got.append)
    assert got == [7]


def test_screen_standalone_default_error_emits_status(qtbot) -> None:
    """Standalone screens route default errors to their status signal."""
    screen = Screen(Backend("healthy"))
    qtbot.addWidget(screen)
    statuses: list[str] = []
    screen.status.connect(statuses.append)
    screen.run_with_wait(
        "op", _boom, on_done=lambda _r: pytest.fail("on_done must not fire")
    )
    assert any("no response from ECU" in s for s in statuses)
