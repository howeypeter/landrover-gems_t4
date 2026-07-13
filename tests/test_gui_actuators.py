"""ActuatorsScreen: success and the characterful engine-running refusal.

Headless (tests/conftest.py forces the offscreen Qt platform). Drives the
screen's run path directly and asserts the outcome the readout reflects.
Requires the ``gui`` extra; skips cleanly if PySide6 is not installed.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.actuators import ActuatorsScreen
from gems_t4.gems import actuators


def test_mil_test_shows_success(qtbot):
    """Driving the MIL on yields an ok outcome shown as 'OK'."""
    screen = ActuatorsScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    screen.on_enter()

    screen._run(actuators.ACT_MIL, actuators.STATE_ON)

    text = screen._readout.text()
    assert text.startswith("OK")
    assert "REFUSED" not in text


def test_fuel_pump_on_is_refused_while_engine_running(qtbot):
    """The fuel pump relay is refused with engine running (ok=False)."""
    backend = Backend("healthy")
    screen = ActuatorsScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    # Confirm the underlying outcome really is a refusal, then the UI reflects it.
    outcome = backend.run_actuator(actuators.ACT_FUEL_PUMP, actuators.STATE_ON)
    assert outcome.ok is False

    screen._run(actuators.ACT_FUEL_PUMP, actuators.STATE_ON)
    assert screen._readout.text().startswith("REFUSED")
    # The refusal names the specific engine-running reason.
    assert "engine is running" in screen._readout.text().lower()


def test_nav_buttons_back_only(qtbot):
    screen = ActuatorsScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    assert screen.nav_buttons() == {"back"}
