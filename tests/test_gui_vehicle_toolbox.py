"""Headless GUI tests for VehicleIdScreen and ToolboxScreen (pytest-qt).

Requires the ``gui`` extra; skips cleanly if PySide6 is not installed.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.toolbox import ToolboxScreen
from gems_t4.app.gui.screens.vehicle_id import VehicleIdScreen


def test_vehicle_id_tick_commits_scenario_and_navigates(qtbot):
    """Selecting a scenario + tick sets it on the backend and navigates onward."""
    backend = Backend("healthy")
    screen = VehicleIdScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    navigated: list[str] = []
    screen.navigate.connect(navigated.append)

    idx = screen._scenario.findText("coolant_sensor")
    assert idx >= 0, "coolant_sensor scenario should be offered in the combo"
    screen._scenario.setCurrentIndex(idx)

    screen.on_tick()

    assert backend.scenario_name == "coolant_sensor"
    assert navigated == ["system_menu"]


def test_toolbox_lan_card_check_shows_canon_disclaimer(qtbot):
    """The LAN card check must surface the verbatim period disclaimer."""
    backend = Backend("healthy")
    screen = ToolboxScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    # Trigger the LAN card check explicitly.
    items = screen._list.findItems("LAN card check", Qt.MatchExactly)
    assert items, "LAN card check should be listed"
    screen._list.setCurrentItem(items[0])

    text = screen._readout.text()
    assert "LAN card: present" in text
    assert "not currently in use" in text
