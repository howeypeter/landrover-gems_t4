"""Headless pytest-qt tests for the coding / settings screen.

Drives the gated write flow end-to-end against the healthy virtual ECU:
selecting a writable field, editing its value, and confirming the two-step
inline Write actually changes the backend's coding block. Also checks that a
read-only field cannot be written.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.coding import CodingScreen


def _select_field(screen: CodingScreen, key: str) -> None:
    """Select the table row whose first-column item carries ``key``."""
    from gems_t4.app.gui.screens.coding import _KEY_ROLE

    table = screen._table
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        if item is not None and item.data(_KEY_ROLE) == key:
            table.selectRow(row)
            return
    raise AssertionError(f"no table row for coding field {key!r}")


def test_coding_populates(qtbot):
    """on_enter fills the table from the backend's coding fields."""
    backend = Backend("healthy")
    screen = CodingScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    assert screen._table.rowCount() == len(backend.coding_fields())
    # vin_last6 is present and shows its current value.
    _select_field(screen, "vin_last6")
    assert screen._value_edit.text() == backend.read_coding_text("vin_last6")


def test_write_vin_last6_through_confirm(qtbot):
    """The two-step Write actually changes vin_last6 in the backend."""
    backend = Backend("healthy")
    screen = CodingScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    _select_field(screen, "vin_last6")
    assert screen._value_edit.isEnabled()
    assert screen._write_btn.isEnabled()

    screen._value_edit.setText("654321")

    # First press arms the confirm; value must NOT be written yet.
    screen._write()
    assert screen._pending_write is True
    assert backend.read_coding_text("vin_last6") != "654321"

    # Second press commits through the gated flow.
    screen._write()
    assert screen._pending_write is False

    assert backend.read_coding_text("vin_last6") == "654321"
    # Readout shows success (green) and mentions the verified write.
    assert "654321" in screen._value_edit.text()
    assert "verified" in screen._readout.text().lower()
    assert "0a7d28" in screen._readout.styleSheet().lower()  # GREEN_OK


def test_readonly_field_cannot_be_written(qtbot):
    """Selecting a read-only field disables Write and refuses if forced."""
    backend = Backend("healthy")
    screen = CodingScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    before = backend.read_coding_text("market")
    _select_field(screen, "market")

    # Editor + Write are disabled for a read-only field.
    assert not screen._value_edit.isEnabled()
    assert not screen._write_btn.isEnabled()

    # Even if _write is invoked directly, it refuses and leaves the value alone.
    screen._write()
    assert backend.read_coding_text("market") == before
    assert "read-only" in screen._readout.text().lower()
    assert "a5140a" in screen._readout.styleSheet().lower()  # RED_BAD
