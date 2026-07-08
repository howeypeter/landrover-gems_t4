"""End-to-end headless GUI QA sweep — walks the WHOLE kiosk like a technician.

The per-screen GUI tests construct each screen standalone; this suite instead
builds the *production* wiring (``gems_t4.app.gui.app.build_window``) and drives
the real :class:`KioskWindow` — navigation history, title bar, nav-button
config, the status bar, and "the waiting" overlay — to catch integration
breakage the unit tests can't see (a screen that blows up only inside the
stack, a nav-button config that never gets applied, a QPainter regression from
the skin work, a wait overlay that never releases the button bar).

Deliberately dynamic: the tour iterates the live screen registry, and the
live-data assertions derive expected gauge counts from ``PARAMETERS`` /
``_COUNT_CHOICES`` at run time, so adding screens or live parameters does not
break this file.

Headless: tests/conftest.py forces the offscreen Qt platform and sets
``GEMS_T4_INSTANT=1`` so waits run synchronously; the overlay-integration test
unsets that via monkeypatch to exercise the real async path. Requires the
``gui`` extra; skips cleanly if PySide6 is not installed.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.app import SCREENS, build_window
from gems_t4.app.gui.base import KioskWindow


@pytest.fixture
def window(qtbot) -> KioskWindow:
    """The real production window: every screen registered, started on boot.

    Shown (offscreen) so widget-visibility checks — nav buttons, the wait
    overlay — behave as they do in the running app.
    """
    win = build_window(Backend("healthy"))
    qtbot.addWidget(win)
    win.show()
    return win


# --------------------------------------------------------------------------- #
# 1. Full navigation tour + Back through the history stack
# --------------------------------------------------------------------------- #
def test_full_navigation_tour_and_back(window: KioskWindow) -> None:
    """Visit EVERY registered screen through the real window, then Back home.

    For each screen: ``on_enter`` must not raise (``go`` calls it), the title
    bar must show the screen's title, and the tick/cross/back buttons must
    match the screen's ``nav_buttons()`` declaration and labels. Then pop the
    whole history stack with Back and land where we started.
    """
    # Derive the tour from the live registry, not a hardcoded list.
    names = list(window._screens)
    assert set(names) == set(SCREENS)  # production registry made it into the shell
    start = window.current_name()
    assert start == names[0]  # the app starts on its first registered screen

    visited: list[str] = []
    for name in names:
        window.go(name)  # runs on_leave/on_enter — must not raise
        assert window.current_name() == name
        screen = window._screens[name]

        # Title bar reflects the screen.
        assert window._title.text() == screen.title

        # Nav-button config was applied from the screen's declaration.
        wanted = screen.nav_buttons()
        assert wanted <= {"back", "cross", "tick"}
        assert window._btn_back.isVisible() == ("back" in wanted)
        assert window._btn_cross.isVisible() == ("cross" in wanted)
        assert window._btn_tick.isVisible() == ("tick" in wanted)
        assert window._btn_tick.text() == screen.tick_label()
        assert window._btn_cross.text() == screen.cross_label()

        visited.append(name)

    # Drive Back through the entire history stack: each pop must land on the
    # previously visited screen, ending at the start with an empty stack.
    # (go() only pushes on a real transition, so the expected trail is the
    # visit list minus the final screen, walked in reverse.)
    trail = visited[:-1]
    for expected in reversed(trail):
        window.back()
        assert window.current_name() == expected
    assert window.current_name() == start
    assert window._history == []


# --------------------------------------------------------------------------- #
# 2. A realistic diagnostic session on misfire_cyl3
# --------------------------------------------------------------------------- #
def test_misfire_diagnostic_session(window: KioskWindow) -> None:
    """Boot → vehicle id (pick misfire_cyl3, tick) → fault codes → clear → re-read.

    The technician's core loop, driven through the public nav handlers just as
    the button bar would: the vehicle-id tick commits the scenario and
    navigates on; the fault-codes screen shows the misfire DTC; the two-step
    cross-cross confirm clears; the tick re-read confirms the ECU is clean.
    """
    # Boot screen's tick is the "press tick to begin" — takes us to vehicle id.
    window._delegate("on_tick")
    assert window.current_name() == "vehicle_id"

    vid = window._screens["vehicle_id"]
    idx = vid._scenario.findText("misfire_cyl3")
    assert idx >= 0, "misfire_cyl3 scenario missing from the vehicle-id combo"
    vid._scenario.setCurrentIndex(idx)
    vid.on_tick()  # commit scenario + connect (instant mode: inline) + navigate

    assert window.current_name() == "system_menu"
    assert window.backend.scenario_name == "misfire_cyl3"
    assert window.backend.connected

    # On to fault codes — on_enter reads the DTCs into the table.
    window.go("fault_codes")
    fc = window._screens["fault_codes"]

    # Derive the expectation from the backend rather than hardcoding a list —
    # but the cylinder-3 misfire DTC itself is contract (see scenarios).
    expected = {d.code for d in window.backend.read_dtcs()}
    assert expected, "misfire_cyl3 must store at least one DTC"
    assert "P0303" in expected  # the canon cylinder-3 misfire code
    shown = {
        fc._table.item(row, 0).text() for row in range(fc._table.rowCount())
    }
    assert expected <= shown

    # Clear via the two-step cross confirm (first press arms, second commits).
    fc.on_cross()
    assert fc._table.rowCount() == len(shown)  # nothing cleared yet
    assert "confirm" in window._status.text().lower()
    fc.on_cross()
    assert fc._table.rowCount() == 0
    assert window.backend.read_dtcs() == []

    # Tick = re-read: still clean.
    fc.on_tick()
    assert fc._table.rowCount() == 0
    assert "no fault codes" in window._status.text().lower()


# --------------------------------------------------------------------------- #
# 3. Live-data smoke: timer ticks, gauge-count sweep, bandwidth trade-off
# --------------------------------------------------------------------------- #
def test_live_data_gauge_sweep(qtbot, window: KioskWindow, monkeypatch) -> None:
    """Enter live data inside the real window, watch the timer actually sweep,
    then run the gauge-count combo through every choice.

    Expected gauge counts are derived from the parameter catalogue at run time
    (``PARAMETERS`` is being extended), the grid must rebuild cleanly on every
    change, and the refresh interval must grow with the gauge count — the
    authentic K-line bandwidth trade-off (CLAUDE.md design pillar 3).
    """
    from gems_t4.gems.livedata import PARAMETERS

    window.go("live_data")
    screen = window._screens["live_data"]
    assert screen._timer.isActive()

    # Prove the timer really sweeps: count backend reads without faking data.
    reads: list[int] = []
    real_read = window.backend.read_live

    def counting_read(ids=None):
        reads.append(1)
        return real_read(ids)

    monkeypatch.setattr(window.backend, "read_live", counting_read)
    screen._count_box.setCurrentIndex(0)  # fewest gauges = fastest cadence
    qtbot.waitUntil(lambda: len(reads) >= 3, timeout=5000)

    # Sweep every combo choice (including "All gauges", wherever it sits).
    counts: list[int] = []
    intervals: list[int] = []
    for i in range(screen._count_box.count()):
        screen._count_box.setCurrentIndex(i)  # rebuilds the grid — must not raise
        n = screen._selected_count()
        assert len(screen._gauges) == n
        assert screen._grid.count() == n
        counts.append(n)
        intervals.append(screen._interval_ms())

    # "All gauges" really means the whole catalogue…
    assert max(counts) == len(PARAMETERS)
    # …and more gauges means a slower sweep (monotonic in gauge count).
    by_count = sorted(zip(counts, intervals))
    assert [ms for _n, ms in by_count] == sorted(intervals)
    assert by_count[-1][1] > by_count[0][1]

    # Leaving the screen through the window stops the sweep.
    window.go("system_menu")
    assert not screen._timer.isActive()


# --------------------------------------------------------------------------- #
# 4. Actuator refusal character, through the real window
# --------------------------------------------------------------------------- #
def test_actuator_refusal_surfaces_in_window(window: KioskWindow) -> None:
    """Run an actuator that must refuse (engine running) and see the refusal
    land on both the screen readout and the window status bar."""
    from gems_t4.gems.actuators import STATE_ON

    window.go("actuators")
    screen = window._screens["actuators"]

    # Pick the refusing actuator from the catalogue, not by hardcoded id: the
    # healthy scenario idles the engine, so anything not allowed with the
    # engine running must come back refused.
    act = next(
        a for a in window.backend.actuator_list() if not a.allowed_engine_running
    )
    screen._run(act.actuator_id, STATE_ON)  # instant mode: completes inline

    assert screen._readout.text().startswith("REFUSED")
    # The refusal message is echoed to the window status bar via the screen's
    # status signal — the wiring under test here.
    assert window._status.text()
    assert window._status.text() in screen._readout.text()


# --------------------------------------------------------------------------- #
# 5. "The waiting" overlay, integrated: overlay up, bar locked, result lands
# --------------------------------------------------------------------------- #
def test_wait_overlay_integration(qtbot, window: KioskWindow, monkeypatch) -> None:
    """Async wait path through a real screen operation inside the real window.

    With instant mode off and a tiny minimum wait, a fault-code read must show
    the overlay, disable the nav bar, then hide, re-enable the bar, and deliver
    the freshly read DTCs into the table.
    """
    from gems_t4.app.gui import wait as wait_mod

    env = getattr(wait_mod, "ENV_INSTANT", None)
    if env is None or not hasattr(wait_mod, "DEFAULT_MIN_WAIT_MS"):
        pytest.skip("wait.py does not expose ENV_INSTANT/DEFAULT_MIN_WAIT_MS")
    controller = getattr(window, "_wait", None)
    if controller is None:
        pytest.skip("KioskWindow does not expose its WaitController")

    # Arrange while still instant: a scenario with codes, on the fault screen.
    window.backend.set_scenario("coolant_sensor")
    window.go("fault_codes")
    screen = window._screens["fault_codes"]
    screen._table.setRowCount(0)  # so we can watch the async result land

    # Now flip to the real async path with a short (but non-zero) minimum wait.
    monkeypatch.delenv(env, raising=False)
    monkeypatch.setattr(wait_mod, "DEFAULT_MIN_WAIT_MS", 30)

    screen.on_tick()  # re-read behind the overlay

    # Immediately after the call: the wait is in flight, the bar is locked,
    # and nothing has been delivered yet (no event loop turn has run).
    assert controller.active
    assert controller.overlay.isVisible()
    assert not window._bar.isEnabled()
    assert screen._table.rowCount() == 0

    # The result lands on the GUI thread once work + minimum wait complete.
    qtbot.waitUntil(lambda: screen._table.rowCount() > 0, timeout=5000)
    assert not controller.active
    assert not controller.overlay.isVisible()
    assert window._bar.isEnabled()
    shown = {screen._table.item(r, 0).text() for r in range(screen._table.rowCount())}
    assert "P0118" in shown  # the coolant-sensor scenario's code arrived intact


# --------------------------------------------------------------------------- #
# 6. Paint smoke: every screen grab()s inside the shell without error
# --------------------------------------------------------------------------- #
def test_every_screen_grabs(window: KioskWindow) -> None:
    """Render every screen to a pixmap through the real window.

    ``grab()`` runs the full paint path (QSS, custom-painted gauges, tables),
    so a QPainter regression from the skin/widget work fails here even when
    the logic tests still pass.
    """
    for name in list(window._screens):
        window.go(name)
        pm = window.grab()  # the whole kiosk: title, screen, status, button bar
        assert not pm.isNull(), f"window grab failed on {name!r}"
        assert pm.width() > 0 and pm.height() > 0
        pm_screen = window._screens[name].grab()  # the screen widget alone
        assert not pm_screen.isNull(), f"screen grab failed on {name!r}"
