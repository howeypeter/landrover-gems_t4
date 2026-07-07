"""Headless GUI tests for the gauge-based :class:`LiveDataScreen`.

Verifies real behaviour: gauges are built from the backend selection, the
gauge-count selector drives both the gauge count and the timer cadence (more
gauges = slower), values are pushed onto gauges, and the timer stops on leave /
pause.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.live_data import LiveDataScreen


def test_gauges_built_and_timer_runs(qtbot):
    screen = LiveDataScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    screen.on_enter()
    assert len(screen._gauges) == screen._selected_count()
    # coolant (0x01) gauge exists and shows a warmed-up value.
    assert 0x01 in screen._gauges
    assert 70 <= screen._gauges[0x01].value() <= 95
    assert screen._timer.isActive()
    screen.on_leave()
    assert not screen._timer.isActive()


def test_more_gauges_slows_refresh(qtbot):
    screen = LiveDataScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    screen.on_enter()
    screen._count_box.setCurrentIndex(0)  # 1 gauge
    fast = screen._interval_ms()
    n_few = len(screen._gauges)
    screen._count_box.setCurrentIndex(4)  # all gauges
    slow = screen._interval_ms()
    assert slow > fast
    assert len(screen._gauges) > n_few
    screen.on_leave()


def test_pause_stops_timer(qtbot):
    screen = LiveDataScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    screen.on_enter()
    assert screen._timer.isActive()
    screen.on_tick()  # pause
    assert not screen._timer.isActive()
    assert screen.tick_label() == "Resume"
    screen.on_tick()  # resume
    assert screen._timer.isActive()
    screen.on_leave()


def test_refresh_pushes_values(qtbot):
    screen = LiveDataScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    screen.on_enter()
    # rpm gauge should hold a positive value after a refresh.
    screen._count_box.setCurrentIndex(4)  # ensure rpm (0x02) is shown
    screen._refresh()
    assert screen._gauges[0x02].value() > 0
    screen.on_leave()
