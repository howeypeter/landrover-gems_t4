"""Headless GUI tests for :class:`LiveDataScreen`.

Verifies real behaviour: the table populates from the backend, the gauge-count
selector drives both the row count and the timer cadence (more gauges = slower),
a timer tick refreshes cell text in place, and the timer stops on leave.
Requires the ``gui`` extra; skips cleanly if PySide6 is not installed.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.live_data import LiveDataScreen


def _make(qtbot) -> LiveDataScreen:
    screen = LiveDataScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    return screen


def test_populates_and_shows_coolant(qtbot) -> None:
    screen = _make(qtbot)
    screen.on_enter()

    # default selection is 4 gauges → 4 rows
    assert screen._table.rowCount() == 4

    names = {
        screen._table.item(r, 0).text()
        for r in range(screen._table.rowCount())
    }
    assert any("Coolant" in n for n in names)

    # value/unit cells are filled, not empty
    assert screen._table.item(0, 1) is not None
    assert screen._table.item(0, 1).text() != ""

    # timer is running after entry
    assert screen._timer.isActive()

    screen.on_leave()
    assert not screen._timer.isActive()


def test_more_gauges_means_slower(qtbot) -> None:
    screen = _make(qtbot)
    screen.on_enter()

    # 1 gauge → fastest
    screen._count_box.setCurrentIndex(0)
    assert screen._table.rowCount() == 1
    fast = screen._interval_ms()

    # all gauges → slowest, and more rows
    all_index = screen._count_box.count() - 1
    screen._count_box.setCurrentIndex(all_index)
    slow = screen._interval_ms()

    assert screen._table.rowCount() > 4
    assert slow > fast  # the bandwidth trade-off is real

    screen.on_leave()
    assert not screen._timer.isActive()


def test_tick_refreshes_in_place(qtbot) -> None:
    screen = _make(qtbot)
    screen.on_enter()

    rows_before = screen._table.rowCount()
    ids_before = {id(screen._table.item(r, 1)) for r in range(rows_before)}

    # simulate a timer tick directly
    screen._refresh()

    # same row objects reused (updated in place, not rebuilt)
    rows_after = screen._table.rowCount()
    ids_after = {id(screen._table.item(r, 1)) for r in range(rows_after)}
    assert rows_after == rows_before
    assert ids_before == ids_after

    screen.on_leave()
    assert not screen._timer.isActive()


def test_pause_stops_timer(qtbot) -> None:
    screen = _make(qtbot)
    screen.on_enter()
    assert screen._timer.isActive()

    screen.on_tick()  # pause
    assert not screen._timer.isActive()

    screen.on_tick()  # resume
    assert screen._timer.isActive()

    screen.on_leave()
    assert not screen._timer.isActive()
