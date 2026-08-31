"""Backend real-ECU (K-line / ISO 9141-2) path.

Verifies that the GUI/CLI Backend, when on a real ECU, routes live data and
fault codes through the KlineClient (mapped to the shared Measure/Dtc types)
and refuses the proprietary services (actuator/coding/immobiliser) that aren't
reverse-engineered yet.
"""
from __future__ import annotations

import pytest

from gems_t4.app.backend import Backend, RealEcuUnsupported
from gems_t4.protocol import kline
from gems_t4.transport.base import InitResult, Transport, TransportTimeout


def _resp(*data: int) -> bytes:
    frame = bytes([0x48, 0x6B, 0xE8]) + bytes(data)
    return frame + bytes([kline.obd_checksum(frame)])


class FakeKlineEcu(Transport):
    def __init__(self, responses: dict[str, bytes]) -> None:
        self.responses = responses
        self._pending: bytes | None = None
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def init(self, address: int, mode: str = "slow") -> InitResult:
        assert address == kline.KLINE_INIT_ADDRESS
        return InitResult()

    def send(self, frame: bytes) -> None:
        resp = self.responses.get(frame[3:-1].hex())
        if resp is None:
            raise TransportTimeout("silent ECU")
        self._pending = resp

    def receive(self, timeout: float | None = None) -> bytes:
        if self._pending is None:
            raise TransportTimeout("no buffered response")
        frame, self._pending = self._pending, None
        return frame


RESPONSES = {
    "0100": _resp(0x41, 0x00, 0xBF, 0x9F, 0xF9, 0x91),  # supported PIDs mask
    "0105": _resp(0x41, 0x05, 0x00),        # coolant 0x00 -> -40 C
    "010c": _resp(0x41, 0x0C, 0x00, 0x00),  # rpm 0
    "03": _resp(0x43, 0x01, 0x18),          # one stored DTC -> P0118
    "04": _resp(0x44),                      # clear accepted
}


def _real_backend() -> Backend:
    """A Backend wired to a fake real ECU (as a USB connection would be)."""
    backend = Backend()
    backend._use_kline = True  # what set_connection("usb", ...) sets
    backend._transport_factory = lambda: FakeKlineEcu(dict(RESPONSES))
    return backend


def test_on_real_ecu_flag() -> None:
    backend = _real_backend()
    assert backend.on_real_ecu is False  # not until connected
    backend.connect()
    assert backend.on_real_ecu is True
    assert backend.connected is True
    backend.disconnect()
    assert backend.connected is False


def test_read_live_maps_obd_to_measures() -> None:
    backend = _real_backend()
    backend.connect()
    measures = backend.read_live()
    by_pid = {m.raw: m for m in measures}
    assert 0x05 in by_pid and by_pid[0x05].value == -40
    assert by_pid[0x05].name == "Coolant temp"
    assert 0x0C in by_pid and by_pid[0x0C].value == 0


def test_read_live_subset_polls_only_selected() -> None:
    backend = _real_backend()
    backend.connect()
    rows = backend.read_live([0x05])
    assert [m.raw for m in rows] == [0x05]


def test_read_dtcs_maps_to_dtc_objects() -> None:
    backend = _real_backend()
    backend.connect()
    dtcs = backend.read_dtcs()
    assert [d.code for d in dtcs] == ["P0118"]


def test_clear_dtcs_ok() -> None:
    backend = _real_backend()
    backend.connect()
    backend.clear_dtcs()  # Mode 04 -> 0x44, must not raise


@pytest.mark.parametrize(
    "call",
    [
        lambda b: b.run_actuator(0x01, 1),
        lambda b: b.immobiliser_status(),
        lambda b: b.read_coding("vin_last6"),
        lambda b: b.security_access(),
    ],
)
def test_proprietary_services_refused_on_real_ecu(call) -> None:
    backend = _real_backend()
    backend.connect()
    with pytest.raises(RealEcuUnsupported):
        call(backend)
