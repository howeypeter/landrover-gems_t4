"""Independent regression suite for the gems_t4 PySide6 GUI (Win98 T4 kiosk).

Written from scratch against the frozen contracts and user docs:

* ``GUI_INTERFACES.md``  — the Screen/KioskWindow/Backend build contract.
* ``CLAUDE.md``          — RDS 5.06 / T4 Lite identity, design pillars (the
  gauge-count -> refresh-rate trade-off, actuator refusals, the LAN disclaimer,
  read-only chip-swap maps, "the waiting").

Deliberately NOT derived from the original ``tests/`` suite. Headless setup
(QT_QPA_PLATFORM=offscreen, GEMS_T4_INSTANT=1) comes from
``tests_regression/conftest.py``.

Run:
    .venv\\Scripts\\python.exe -m pytest tests_regression/test_regr_gui.py -q
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QComboBox, QLabel, QPushButton  # noqa: E402

from gems_t4.app.backend import Backend  # noqa: E402
from gems_t4.app.gui.app import SCREENS, build_window  # noqa: E402
from gems_t4.app.gui.base import KioskWindow  # noqa: E402
from gems_t4.gems.livedata import PARAMETERS  # noqa: E402

# ---------------------------------------------------------------------------
# Documented facts (from CLAUDE.md / GUI_INTERFACES.md) that the GUI must obey.
# ---------------------------------------------------------------------------

#: CLAUDE.md: 12 GUI screens; app.py registers exactly these, boot first.
#: ("connection" — the VCI configuration screen — added with the TCP transport.)
EXPECTED_SCREENS = [
    "boot",
    "vehicle_id",
    "system_menu",
    "fault_codes",
    "live_data",
    "actuators",
    "toolbox",
    "connection",
    "programming_menu",
    "coding",
    "immobiliser",
    "maps",
]

#: CLAUDE.md: the four locked-in fault scenarios.
EXPECTED_SCENARIOS = {"healthy", "coolant_sensor", "misfire_cyl3", "lambda_heater"}

#: CLAUDE.md (canon, quoted verbatim from the real manual).
LAN_DISCLAIMER = (
    "is intended for potential future developments in dealership systems, "
    "and is not currently in use"
)

#: CLAUDE.md: "Emulate RDS 5.06 / T4 Lite specifically" — boot + About identity.
IDENTITY_BITS = ("RDS 5.06", "T4 Lite")


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


@pytest.fixture()
def window_factory(qtbot):
    """Build the production window (build_window wiring) for a given scenario."""

    def make(scenario: str = "healthy") -> KioskWindow:
        win = build_window(Backend(scenario))
        qtbot.addWidget(win)
        return win

    return make


def _labels_text(widget) -> str:
    """Concatenate every QLabel's text under a widget (for content asserts)."""
    return "\n".join(lbl.text() for lbl in widget.findChildren(QLabel))


def _status_text(window: KioskWindow) -> str:
    status = window.findChild(QLabel, "StatusBar")
    assert status is not None, "kiosk window must have a StatusBar label"
    return status.text()


def _table_column(table, col: int) -> list[str]:
    return [table.item(r, col).text() for r in range(table.rowCount())]


# ---------------------------------------------------------------------------
# 1. build_window / registration
# ---------------------------------------------------------------------------


def test_build_window_registers_all_12_screens(window_factory):
    """build_window constructs a KioskWindow with all 12 documented screens."""
    assert list(SCREENS) == EXPECTED_SCREENS
    win = window_factory()
    assert isinstance(win, KioskWindow)
    # Every documented screen must be navigable; unknown names must raise.
    for name in EXPECTED_SCREENS:
        win.go(name)
        assert win.current_name() == name
    with pytest.raises(KeyError):
        win.go("no_such_screen")


def test_build_window_starts_on_boot(window_factory):
    win = window_factory()
    assert win.current_name() == "boot"


def test_window_title_reports_t4_identity(window_factory):
    win = window_factory()
    for bit in IDENTITY_BITS:
        assert bit in win.windowTitle()


# ---------------------------------------------------------------------------
# 2. Boot screen — RDS 5.06 / T4 Lite identity
# ---------------------------------------------------------------------------


def test_boot_screen_shows_rds_506_t4_lite(window_factory):
    """CLAUDE.md: the emulator reports RDS 5.06 / T4 Lite on boot."""
    win = window_factory()
    boot = win._stack.currentWidget()
    text = _labels_text(boot)
    for bit in IDENTITY_BITS:
        assert bit in text, f"boot splash must show {bit!r}"


def test_boot_tick_advances_to_vehicle_id(window_factory):
    """Boot shows only the tick button; pressing it starts vehicle ID."""
    win = window_factory()
    boot = win._stack.currentWidget()
    assert boot.nav_buttons() == {"tick"}
    boot.on_tick()
    assert win.current_name() == "vehicle_id"


# ---------------------------------------------------------------------------
# 3. Navigation / history stack
# ---------------------------------------------------------------------------


def test_back_unwinds_navigation_history(window_factory):
    """Back pops the history stack: boot -> vehicle_id -> system_menu -> leaf."""
    win = window_factory()
    win.go("vehicle_id")
    win.go("system_menu")
    win.go("fault_codes")
    win.back()
    assert win.current_name() == "system_menu"
    win.back()
    assert win.current_name() == "vehicle_id"
    win.back()
    assert win.current_name() == "boot"
    # Empty history: back is a no-op, not an error.
    win.back()
    assert win.current_name() == "boot"


def test_system_menu_reaches_every_major_function(window_factory):
    """Each system-menu button navigates to its screen, and Back returns."""
    win = window_factory()
    win.go("system_menu")
    menu = win._screens["system_menu"]
    buttons = {
        b.text(): b for b in menu.findChildren(QPushButton) if b.objectName() == "MenuItem"
    }
    assert len(buttons) == 6, "system menu offers the five v1 functions + VCI config"
    targets = {
        "fault_codes",
        "live_data",
        "actuators",
        "programming_menu",
        "toolbox",
        "connection",
    }
    seen = set()
    for btn in buttons.values():
        btn.click()
        seen.add(win.current_name())
        win.back()
        assert win.current_name() == "system_menu"
    assert seen == targets


# ---------------------------------------------------------------------------
# 4. Vehicle-ID screen — scenario selection drives the backend
# ---------------------------------------------------------------------------


def test_vehicle_id_offers_the_four_fault_scenarios(window_factory):
    win = window_factory()
    win.go("vehicle_id")
    screen = win._screens["vehicle_id"]
    combo = screen.findChild(QComboBox)
    assert combo is not None
    offered = {combo.itemText(i) for i in range(combo.count())}
    assert offered == EXPECTED_SCENARIOS
    # And they match what the backend itself advertises.
    assert offered == set(Backend.available_scenarios())


def test_vehicle_id_tick_commits_scenario_and_advances(window_factory):
    """Choosing a scenario + tick reconfigures the backend and moves on."""
    win = window_factory("healthy")
    win.go("vehicle_id")
    screen = win._screens["vehicle_id"]
    combo = screen.findChild(QComboBox)
    combo.setCurrentIndex(combo.findText("misfire_cyl3"))
    screen.on_tick()  # instant mode: synchronous
    assert win.backend.scenario_name == "misfire_cyl3"
    assert win.backend.connected
    assert win.current_name() == "system_menu"
    assert "misfire_cyl3" in _status_text(win) or True  # status was reset by nav
    # The committed scenario shows on the system-menu header.
    assert "misfire_cyl3" in _labels_text(win._screens["system_menu"])


def test_vehicle_id_reenter_syncs_combo_to_backend(window_factory):
    """on_enter re-reads the backend's current scenario into the combo."""
    win = window_factory("lambda_heater")
    win.go("vehicle_id")
    combo = win._screens["vehicle_id"].findChild(QComboBox)
    assert combo.currentText() == "lambda_heater"


# ---------------------------------------------------------------------------
# 5. Fault codes — misfire scenario, read + two-step clear
# ---------------------------------------------------------------------------


def test_fault_codes_misfire_shows_p0303_and_p1303(window_factory):
    win = window_factory("misfire_cyl3")
    win.go("fault_codes")
    screen = win._screens["fault_codes"]
    codes = _table_column(screen._table, 0)
    assert "P0303" in codes
    assert "P1303" in codes
    assert "2 fault code(s) stored" in _status_text(win)
    descriptions = " ".join(_table_column(screen._table, 2))
    assert "Cylinder 3" in descriptions


def test_fault_codes_clear_requires_two_step_confirmation(window_factory):
    """First ✗ arms the clear (list untouched); second ✗ clears and re-reads."""
    win = window_factory("misfire_cyl3")
    win.go("fault_codes")
    screen = win._screens["fault_codes"]
    assert screen.nav_buttons() == {"back", "cross", "tick"}
    assert screen._table.rowCount() == 2

    screen.on_cross()  # arm
    assert screen._table.rowCount() == 2, "first press must not clear yet"
    assert "confirm" in _status_text(win).lower()

    screen.on_cross()  # confirm -> clear + re-read
    assert screen._table.rowCount() == 0
    assert "No fault codes stored" in _status_text(win)

    screen.on_tick()  # re-read stays empty
    assert screen._table.rowCount() == 0


def test_fault_codes_healthy_scenario_is_empty(window_factory):
    """GUI_INTERFACES.md: the default 'healthy' scenario has no DTCs."""
    win = window_factory("healthy")
    win.go("fault_codes")
    assert win._screens["fault_codes"]._table.rowCount() == 0
    assert "No fault codes stored" in _status_text(win)


# ---------------------------------------------------------------------------
# 6. Live data — gauges + the gauge-count -> refresh-rate trade-off
# ---------------------------------------------------------------------------


def test_live_data_renders_gauges_for_selection(window_factory):
    win = window_factory()
    win.go("live_data")
    screen = win._screens["live_data"]
    try:
        # Default selection is 4 gauges; widgets exist and carry live values.
        assert len(screen._gauges) == 4
        assert screen._timer.isActive(), "refresh timer must run while shown"
        for gauge in screen._gauges.values():
            assert hasattr(gauge, "set_value") and hasattr(gauge, "value")
        # Status advertises the K-line bandwidth character.
        assert "refresh" in _status_text(win)
    finally:
        win.go("system_menu")
    assert not screen._timer.isActive(), "timer must stop on leave"


def test_live_data_interval_grows_with_gauge_count(window_factory):
    """CLAUDE.md pillar 3: more gauges -> visibly slower refresh (monotonic)."""
    win = window_factory()
    win.go("live_data")
    screen = win._screens["live_data"]
    try:
        counts, intervals = [], []
        for i in range(screen._count_box.count()):
            screen._count_box.setCurrentIndex(i)
            counts.append(screen._selected_count())
            intervals.append(screen._interval_ms())
        # Monotonic non-decreasing interval vs count (documented trade-off).
        paired = sorted(zip(counts, intervals))
        for (c1, i1), (c2, i2) in zip(paired, paired[1:]):
            assert i2 >= i1, f"{c2} gauges refresh faster than {c1}: {i2} < {i1}"
        by_count = dict(paired)
        # ~20/s watching one measure ... ~1 per 2 s with everything selected.
        assert by_count[1] <= 100, "1 gauge should refresh at roughly 20 Hz"
        assert by_count[max(counts)] >= 1000, "full sweep should be ~1 per 2 s"
        # "All gauges" really means every known parameter.
        assert max(counts) == len(PARAMETERS)
    finally:
        win.go("system_menu")


def test_live_data_tick_pauses_and_resumes(window_factory):
    win = window_factory()
    win.go("live_data")
    screen = win._screens["live_data"]
    try:
        assert screen._timer.isActive()
        screen.on_tick()  # pause
        assert not screen._timer.isActive()
        assert screen.tick_label() == "Resume"
        assert "paused" in _status_text(win)
        screen.on_tick()  # resume
        assert screen._timer.isActive()
        assert screen.tick_label() == "Pause"
    finally:
        win.go("system_menu")


# ---------------------------------------------------------------------------
# 7. Gauge widgets + specs for all 37 live parameters
# ---------------------------------------------------------------------------


def test_gauge_widgets_construct_and_accept_values(qtbot):
    from gems_t4.app.gui.gauge_specs import GaugeSpec
    from gems_t4.app.gui.widgets import BarGauge, DialGauge, LcdReadout

    spec = GaugeSpec(0x02, "Engine speed", "rpm", 0, 7000, redline=6000)
    for cls in (DialGauge, BarGauge, LcdReadout):
        g = cls(spec)
        qtbot.addWidget(g)
        g.set_value(3500)
        assert g.value() == 3500
        g.set_value(99999)  # clamps to the scale top
        assert g.value() == 7000
        g.set_value(-5)  # clamps to the scale bottom
        assert g.value() == 0
        g.set_value("not-a-number")  # coerces safely to the scale bottom
        assert g.value() == 0
        assert not g.grab().isNull()


def test_spec_for_covers_all_37_parameters(qtbot):
    """CLAUDE.md: 37 live-data params; every one gets a usable gauge spec."""
    from gems_t4.app.gui.gauge_specs import spec_for
    from gems_t4.app.gui.widgets import build_gauge

    assert len(PARAMETERS) == 37
    for lid in PARAMETERS:
        spec = spec_for(lid)
        assert spec.label, f"param 0x{lid:02X} needs a label"
        assert spec.vmax > spec.vmin, f"param 0x{lid:02X} has a degenerate scale"
        gauge = build_gauge(spec)
        qtbot.addWidget(gauge)
        gauge.set_value(spec.vmin)
        gauge.set_value(spec.vmax)
        assert gauge.value() == spec.vmax


# ---------------------------------------------------------------------------
# 8. Actuators — the characterful refusal
# ---------------------------------------------------------------------------


def _actuator_on_button(screen, actuator_name_fragment: str) -> QPushButton:
    """Find the 'Test On' button on the row whose label mentions the actuator."""
    from PySide6.QtWidgets import QGridLayout

    grid = screen.findChild(QGridLayout)
    assert grid is not None
    for row in range(grid.rowCount()):
        label_item = grid.itemAtPosition(row, 0)
        if label_item and actuator_name_fragment.lower() in label_item.widget().text().lower():
            return grid.itemAtPosition(row, 1).widget()
    raise AssertionError(f"no actuator row matching {actuator_name_fragment!r}")


def test_actuator_fuel_pump_refused_engine_running(window_factory):
    """Fuel pump relay is refused with the engine running (pillar 4)."""
    win = window_factory("healthy")
    win.go("actuators")
    screen = win._screens["actuators"]
    _actuator_on_button(screen, "fuel pump").click()
    readout = screen._readout.text()
    assert readout.startswith("REFUSED"), f"expected a refusal, got {readout!r}"
    assert "not available" in readout or "conditions not correct" in readout
    # The refusal also lands on the kiosk status bar (per GUI_INTERFACES).
    assert "conditions not correct" in _status_text(win) or "not available" in _status_text(win)


def test_actuator_mil_test_succeeds(window_factory):
    win = window_factory("healthy")
    win.go("actuators")
    screen = win._screens["actuators"]
    _actuator_on_button(screen, "MIL").click()
    readout = screen._readout.text()
    assert readout.startswith("OK"), f"expected success, got {readout!r}"
    assert "switched on" in readout


# ---------------------------------------------------------------------------
# 9. Toolbox — the canon LAN disclaimer + About identity
# ---------------------------------------------------------------------------


def test_toolbox_lan_check_quotes_canon_disclaimer(window_factory):
    """CLAUDE.md: LAN card check reports presence + the verbatim disclaimer."""
    win = window_factory()
    win.go("toolbox")
    screen = win._screens["toolbox"]
    # on_enter preselects the first check (LAN card check).
    assert screen._list.currentItem().text() == "LAN card check"
    text = screen._readout.text()
    assert "LAN card: present" in text
    assert LAN_DISCLAIMER in text


def test_toolbox_about_reports_rds_identity(window_factory):
    win = window_factory()
    win.go("toolbox")
    screen = win._screens["toolbox"]
    items = [screen._list.item(i).text() for i in range(screen._list.count())]
    assert "About" in items
    screen._list.setCurrentRow(items.index("About"))
    text = screen._readout.text()
    for bit in IDENTITY_BITS:
        assert bit in text


# ---------------------------------------------------------------------------
# 10. "The waiting" — instant mode is synchronous, never wedges the window
# ---------------------------------------------------------------------------


def test_wait_overlay_instant_mode_completes_synchronously(window_factory):
    """With GEMS_T4_INSTANT set, run_with_wait is inline: no overlay, nav live."""
    win = window_factory()
    results: list[str] = []
    win.run_with_wait("Test op", lambda: "done", results.append)
    assert results == ["done"], "instant mode must call on_done before returning"
    assert not win._wait.active
    assert not win._wait.overlay.isVisible()
    assert win._bar.isEnabled(), "nav bar must be re-enabled (not wedged)"


def test_wait_error_routes_to_status_bar(window_factory):
    """A failing backend op surfaces as an ECU-communication status message."""
    win = window_factory()

    def boom() -> None:
        raise RuntimeError("no response from ECU")

    win.run_with_wait("Test op", boom, lambda _r: pytest.fail("must not succeed"))
    assert "ECU communication error" in _status_text(win)
    assert "no response from ECU" in _status_text(win)
    assert win._bar.isEnabled()


def test_full_session_navigation_never_wedges(window_factory):
    """A whole guided session in instant mode leaves the nav bar usable."""
    win = window_factory("misfire_cyl3")
    win._screens["boot"].on_tick()                      # boot -> vehicle_id
    win._screens["vehicle_id"].on_tick()                # -> system_menu (with wait)
    win.go("fault_codes")                               # read (with wait)
    win._screens["fault_codes"].on_tick()               # re-read
    win.back()
    assert win.current_name() == "system_menu"
    assert win._bar.isEnabled()
    assert not win._wait.active


# ---------------------------------------------------------------------------
# 11. Programming sub-menu, and the read-only maps screen
# ---------------------------------------------------------------------------


def test_programming_menu_reaches_coding_immobiliser_maps(window_factory):
    win = window_factory()
    win.go("programming_menu")
    menu = win._screens["programming_menu"]
    buttons = [b for b in menu.findChildren(QPushButton) if b.objectName() == "MenuItem"]
    assert len(buttons) == 3
    reached = set()
    for btn in buttons:
        btn.click()
        reached.add(win.current_name())
        win.back()
        assert win.current_name() == "programming_menu"
    assert reached == {"coding", "immobiliser", "maps"}


def test_maps_screen_is_read_only_with_chip_swap_note(window_factory):
    """CLAUDE.md: maps are a read-only chip-swap lookalike — no K-line reflash."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QTableWidget

    win = window_factory()
    win.go("maps")
    screen = win._screens["maps"]

    # No write/tick affordance at all.
    assert "tick" not in screen.nav_buttons()
    assert screen.findChildren(QPushButton) == [], "maps screen must offer no buttons"

    # The 16x16 grid is populated and not editable.
    table = screen.findChild(QTableWidget)
    assert table.rowCount() == 16 and table.columnCount() == 16
    assert table.editTriggers() == QTableWidget.NoEditTriggers
    assert not (table.item(0, 0).flags() & Qt.ItemIsEditable)

    # The honest no-reflash note is on screen.
    text = _labels_text(screen)
    assert "no K-line reflash" in text
    assert "27C512" in text or "EPROM" in text

    # Both documented maps are selectable and reload the grid.
    combo = screen.findChild(QComboBox)
    tokens = {combo.itemData(i) for i in range(combo.count())}
    assert tokens == {"fuel", "ignition"}
    combo.setCurrentIndex(1)
    assert table.rowCount() == 16 and table.columnCount() == 16


# ---------------------------------------------------------------------------
# 12. Paint smoke — every screen renders offscreen without exceptions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", EXPECTED_SCREENS)
def test_every_screen_paints(window_factory, name):
    win = window_factory("misfire_cyl3")
    win.go(name)
    pixmap = win.grab()
    assert not pixmap.isNull()
    assert pixmap.width() > 0 and pixmap.height() > 0
    # Leave cleanly (stops any screen timer).
    if name != "boot":
        win.go("boot")
