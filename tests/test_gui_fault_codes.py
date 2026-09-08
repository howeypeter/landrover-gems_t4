"""Headless GUI test for the fault-codes re-read fix.

Reproduces the real-ECU bug: codes showed on entry but VANISHED on a second
Read, because the K-line session had gone stale (a second Mode 03 on a dead
session returns silence -> an empty list). The fix re-initialises the session
for each real-ECU read.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.gui.screens.fault_codes import FaultCodesScreen
from gems_t4.gems.types import Dtc, DtcState


class _StaleSessionBackend:
    """A real-ECU-like backend whose session decays after one read.

    A read on a *fresh* session returns a code; a second read of the SAME
    (now stale) session returns ``[]`` (silence). A ``disconnect`` — modelling a
    fresh 5-baud re-init — revives the session so the next read is fresh again.
    """

    on_real_ecu = True

    def __init__(self) -> None:
        self.disconnects = 0
        self._fresh = True

    def read_dtcs(self) -> list[Dtc]:
        codes = (
            [Dtc(code="P0303", description="cyl 3 misfire", state=DtcState.STORED)]
            if self._fresh
            else []
        )
        self._fresh = False  # the live session decays after a read
        return codes

    def disconnect(self) -> None:
        self.disconnects += 1
        self._fresh = True  # a fresh init revives the session


def test_fault_codes_reread_reinits_and_keeps_codes_on_real_ecu(qtbot):
    backend = _StaleSessionBackend()
    screen = FaultCodesScreen(backend)
    qtbot.addWidget(screen)

    screen.on_enter()  # first read -> code shown
    assert screen._table.rowCount() == 1

    screen.on_tick()  # RE-READ: must re-init, not read the stale session
    assert screen._table.rowCount() == 1, "codes must not vanish on re-read"
    assert backend.disconnects >= 1, "the real-ECU re-read must re-initialise"
