"""Headless pytest-qt tests for the read-only engine-maps screen."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.maps import MapsScreen
from gems_t4.gems.maps import CHIP_SWAP_NOTE


def _all_texts(screen: MapsScreen) -> str:
    """Concatenate every QLabel's text on the screen for substring assertions."""
    from PySide6.QtWidgets import QLabel

    return "\n".join(lbl.text() for lbl in screen.findChildren(QLabel))


def test_table_is_16x16_and_cells_match_backend(qtbot) -> None:
    backend = Backend("healthy")
    screen = MapsScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    table = screen._table
    assert table.rowCount() == 16
    assert table.columnCount() == 16

    token = screen._selected_token()
    src = backend.get_map(token)
    # A known cell rendered into the grid matches the source MapTable.
    for r, c in ((0, 0), (7, 9), (15, 15)):
        assert table.item(r, c).text() == f"{src.cell(r, c):g}"


def test_switching_map_reloads_grid(qtbot) -> None:
    backend = Backend("healthy")
    screen = MapsScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    first_token = screen._selected_token()
    first_cell = screen._table.item(0, 0).text()

    # Pick a different map token in the combo.
    other_index = next(
        i
        for i in range(screen._map_box.count())
        if screen._map_box.itemData(i) != first_token
    )
    screen._map_box.setCurrentIndex(other_index)

    second_token = screen._selected_token()
    assert second_token != first_token
    # Still a 16-column grid after reload.
    assert screen._table.columnCount() == 16
    assert screen._table.rowCount() == 16
    # The grid actually reloaded to the new map's data.
    src = backend.get_map(second_token)
    assert screen._table.item(0, 0).text() == f"{src.cell(0, 0):g}"
    # Fuel and ignition surfaces differ, so cell (0,0) should have changed.
    assert screen._table.item(0, 0).text() != first_cell


def test_chip_swap_note_present(qtbot) -> None:
    backend = Backend("healthy")
    screen = MapsScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    texts = _all_texts(screen).lower()
    # The honest "no K-line reflash / bench chip swap" message is present.
    assert "reflash" in texts or "chip" in texts or "swap" in texts
    # The full honest note is surfaced verbatim.
    assert CHIP_SWAP_NOTE in _all_texts(screen)


def test_read_only_no_tick_button(qtbot) -> None:
    backend = Backend("healthy")
    screen = MapsScreen(backend)
    qtbot.addWidget(screen)
    assert screen.nav_buttons() == {"back"}
