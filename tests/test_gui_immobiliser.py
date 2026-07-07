"""Headless (pytest-qt) tests for the immobiliser Security-Learn screen."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.immobiliser import ImmobiliserScreen


def test_shows_immobilised_then_learn_mobilises(qtbot) -> None:
    """Start immobilised, run Security-Learn, end mobilised with a step log."""
    backend = Backend("healthy", immobilised=True)
    screen = ImmobiliserScreen(backend)
    qtbot.addWidget(screen)

    screen.on_enter()

    # The canon failure mode is shown prominently before any action.
    assert "ENGINE IMMOBILISED" in screen._readout.text()
    assert backend.immobiliser_status().mobilised is False

    # Run the Security-Learn re-sync.
    screen._run_security_learn()

    # Multiple live steps streamed into the log (plus a final result line).
    log_lines = [screen._log.item(i).text() for i in range(screen._log.count())]
    assert len(log_lines) > 2
    assert any("Security access" in line for line in log_lines)

    # The ECU is now mobilised and the readout reflects it.
    assert backend.immobiliser_status().mobilised is True
    assert "MOBILISED" in screen._readout.text()

    screen.on_leave()


def test_simulate_button_forces_immobilised(qtbot) -> None:
    """The simulate action forces the failure mode and refreshes the readout."""
    backend = Backend("healthy", immobilised=False)
    screen = ImmobiliserScreen(backend)
    qtbot.addWidget(screen)

    screen.on_enter()
    assert backend.immobiliser_status().mobilised is True
    assert "MOBILISED" in screen._readout.text()

    screen._simulate_immobilised()

    assert backend.immobiliser_status().mobilised is False
    assert "ENGINE IMMOBILISED" in screen._readout.text()


def test_nav_buttons_back_only(qtbot) -> None:
    """The screen only offers the Back nav button."""
    screen = ImmobiliserScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    assert screen.nav_buttons() == {"back"}
