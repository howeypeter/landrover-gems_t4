"""GUI shell + backend: navigation, history, and the backend facade.

Headless (tests/conftest.py forces the offscreen Qt platform). Requires the
``gui`` extra (PySide6 + pytest-qt) — see ``pip install -e ".[gui]"`` in
README.html. Skips cleanly (not an error) if PySide6 is not installed, since
``requirements.txt`` deliberately does not include it.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend


# --------------------------------------------------------------------------- #
# Backend facade (no Qt)
# --------------------------------------------------------------------------- #
def test_backend_reads_scenario_dtcs():
    b = Backend("coolant_sensor")
    b.connect()
    codes = [d.code for d in b.read_dtcs()]
    assert "P0118" in codes
    assert not b.is_wireless


def test_backend_healthy_has_no_dtcs_and_reads_live():
    b = Backend("healthy")
    assert b.read_dtcs() == []          # auto-connects
    measures = b.read_live()
    assert measures and any(m.name.startswith("Coolant") for m in measures)


def test_backend_actuator_refusal():
    from gems_t4.gems import actuators
    b = Backend("healthy")
    outcome = b.run_actuator(actuators.ACT_FUEL_PUMP, actuators.STATE_ON)
    assert not outcome.ok  # engine running -> refused


def test_backend_set_scenario_switches_dtcs():
    b = Backend("healthy")
    assert b.read_dtcs() == []
    b.set_scenario("misfire_cyl3")
    assert "P0303" in [d.code for d in b.read_dtcs()]


def test_backend_clear_dtcs():
    b = Backend("coolant_sensor")
    assert b.read_dtcs()
    b.clear_dtcs()
    assert b.read_dtcs() == []


# --------------------------------------------------------------------------- #
# Kiosk window / navigation
# --------------------------------------------------------------------------- #
@pytest.fixture
def window(qtbot):
    from gems_t4.app.gui.app import build_window
    win = build_window(Backend("coolant_sensor"))
    qtbot.addWidget(win)
    return win


def test_all_screens_registered_and_starts_on_boot(window):
    from gems_t4.app.gui.app import SCREENS
    assert set(window._screens) == set(SCREENS)
    assert window.current_name() == "boot"


def test_navigation_and_back(window):
    window.go("vehicle_id")
    window.go("system_menu")
    assert window.current_name() == "system_menu"
    window.back()
    assert window.current_name() == "vehicle_id"
    window.back()
    assert window.current_name() == "boot"


def test_title_updates_with_screen(window):
    window.go("fault_codes")
    assert window._title.text() == window._screens["fault_codes"].title


def test_nav_button_delegation_reaches_current_screen(window):
    # boot screen's tick navigates to vehicle_id
    window._delegate("on_tick")
    assert window.current_name() == "vehicle_id"


# --------------------------------------------------------------------------- #
# Persistent connection indicator — visible on every screen, one click to the
# Configuration screen (so changing/testing the VCI link never requires
# hunting through the System menu).
# --------------------------------------------------------------------------- #

def test_connection_indicator_shows_current_label(window):
    assert window.backend.connection_label in window._btn_connection.text()


def test_connection_indicator_present_on_every_screen(window):
    """It lives in the persistent title-bar chrome, not per-screen content —
    the same widget instance stays put and up to date across every
    navigation, rather than being rebuilt or hidden per screen."""
    indicator = window._btn_connection
    for name in window._screens:
        window.go(name)
        assert window._btn_connection is indicator  # same persistent widget
        assert "VCI:" in indicator.text()


def test_clicking_connection_indicator_navigates_to_connection_screen(window):
    window.go("fault_codes")
    window._btn_connection.click()
    assert window.current_name() == "connection"


def test_connection_indicator_updates_after_reconnecting(window):
    from gems_t4.app.gui.screens.connection import ConnectionScreen

    window.go("connection")
    screen = window._screens["connection"]
    assert isinstance(screen, ConnectionScreen)
    before = window._btn_connection.text()

    window.backend.set_connection("usb", com_port="COM7")
    screen._refresh_window_indicator()
    after = window._btn_connection.text()

    assert before != after
    assert "COM7" in after
