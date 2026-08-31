"""The GUI live-data screen driven by a real ECU (K-line / OBD-II) backend.

Confirms the screen discovers the ECU's supported OBD PIDs, builds gauges from
them (not the stylized param set), and refreshes without raising.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.gui.screens.live_data import LiveDataScreen
from gems_t4.protocol import kline
from gems_t4.transport.base import InitResult, Transport, TransportTimeout


def _resp(*data: int) -> bytes:
    frame = bytes([0x48, 0x6B, 0xE8]) + bytes(data)
    return frame + bytes([kline.obd_checksum(frame)])


class _FakeKlineEcu(Transport):
    RESPONSES = {
        "0100": _resp(0x41, 0x00, 0xBF, 0x9F, 0xF9, 0x91),  # supported mask
        "0105": _resp(0x41, 0x05, 0x00),        # coolant -40
        "010c": _resp(0x41, 0x0C, 0x0A, 0xF0),  # rpm 700
        "0111": _resp(0x41, 0x11, 0x33),        # throttle ~20 %
    }

    def __init__(self) -> None:
        self._pending: bytes | None = None
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def init(self, address: int, mode: str = "slow") -> InitResult:
        return InitResult()

    def send(self, frame: bytes) -> None:
        resp = self.RESPONSES.get(frame[3:-1].hex())
        if resp is None:
            raise TransportTimeout("silent")
        self._pending = resp

    def receive(self, timeout: float | None = None) -> bytes:
        if self._pending is None:
            raise TransportTimeout("none")
        frame, self._pending = self._pending, None
        return frame


def _real_backend() -> Backend:
    backend = Backend()
    backend._use_kline = True
    backend._transport_factory = lambda: _FakeKlineEcu()
    return backend


def test_live_screen_builds_obd_gauges_and_refreshes(qtbot) -> None:
    backend = _real_backend()
    backend.connect()
    screen = LiveDataScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()
    try:
        assert screen._real is True
        # Gauges came from the ECU's answered OBD PIDs, not the stylized set.
        assert len(screen._gauges) >= 1
        assert set(screen._gauges).issubset({0x05, 0x0C, 0x11})
        screen._refresh()  # a sweep must not raise against the real profile
    finally:
        screen.on_leave()
