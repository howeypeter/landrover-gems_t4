"""Backend facade: :meth:`Backend.test_connection` (no Qt).

Covers the "test that the connection is working, connection speed" feature:
the virtual ECU always reports OK with no round-trip to measure; a transport
with a ``ping()`` method (USB/network) gets its latency measured; a transport
without one still reports OK; a failing connection reports not-OK; and an
already-open session is reused rather than opening a second connection.
"""
from __future__ import annotations

from gems_t4.app.backend import Backend
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.transport.base import Transport, TransportError
from gems_t4.transport.virtual import VirtualTransport


class _PingableTransport(VirtualTransport):
    """A VirtualTransport that also answers the host-protocol PING, so
    Backend.test_connection can measure a (near-instant) round trip."""

    def ping(self) -> bytes:
        return b"fake v1"


class _FailingTransport(Transport):
    """A transport whose open() always fails (simulates an unreachable link)."""

    def open(self) -> None:
        raise TransportError("simulated link failure")

    def close(self) -> None:
        pass

    def is_open(self) -> bool:
        return False

    def init(self, address: int, mode: str = "slow"):  # pragma: no cover
        raise TransportError("unreachable")

    def send(self, frame: bytes) -> None:  # pragma: no cover
        raise TransportError("unreachable")

    def receive(self, timeout: float | None = None) -> bytes:  # pragma: no cover
        raise TransportError("unreachable")


def _fresh_ecu() -> VirtualEcu:
    return VirtualEcu(get_scenario("healthy"))


def test_virtual_ecu_reports_ok_with_no_latency():
    b = Backend("healthy")
    result = b.test_connection()
    assert result.ok
    assert "Virtual ECU" in result.message
    assert result.latencies_ms == ()


def test_pingable_transport_measures_latency():
    b = Backend(transport_factory=lambda: _PingableTransport(_fresh_ecu()))
    result = b.test_connection(pings=3)
    assert result.ok
    assert len(result.latencies_ms) == 3
    assert all(ms >= 0 for ms in result.latencies_ms)
    assert "3/3 replies" in result.message


def test_transport_without_ping_still_reports_connected():
    b = Backend(transport_factory=lambda: VirtualTransport(_fresh_ecu()))
    result = b.test_connection()
    assert result.ok
    assert result.latencies_ms == ()
    assert "no round-trip probe" in result.message.lower()


def test_failed_connection_reports_not_ok():
    b = Backend(transport_factory=_FailingTransport)
    result = b.test_connection()
    assert not result.ok
    assert "failed" in result.message.lower() or "error" in result.message.lower()


def test_zero_pings_does_not_crash():
    b = Backend(transport_factory=lambda: _PingableTransport(_fresh_ecu()))
    result = b.test_connection(pings=0)
    assert result.ok
    assert result.latencies_ms == ()


def test_reuses_already_open_session_no_second_connection():
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return _PingableTransport(_fresh_ecu())

    b = Backend(transport_factory=factory)
    b.connect()
    assert calls["n"] == 1
    result = b.test_connection(pings=2)
    assert result.ok
    assert calls["n"] == 1  # no second transport was built


# -- apply_connection() rollback restores the FULL connection state ---------- #
# A failed attempt used to leave _kind and _use_kline pointing at the failed
# connection while the transport/label rolled back. The _use_kline leak was the
# damaging one: the restored virtual ECU was then driven with the real-ECU
# K-line profile. Rolling back from "usb"/"ble" is what exposes it — a
# "network" attempt happens to share virtual's _use_kline=False.
def test_failed_usb_attempt_rolls_back_kind_and_profile():
    b = Backend()  # virtual ECU, stylized KWP profile
    b.connect()
    assert b.connection_kind == "virtual"

    try:
        b.apply_connection("usb", com_port="COM_NO_SUCH_PORT_99")
    except Exception:
        pass
    else:  # pragma: no cover - the bogus port must not open
        raise AssertionError("expected the bogus COM port to fail")

    assert b.connection_kind == "virtual", "kind must roll back (drives connect_help)"
    assert b.connection_label == "Virtual ECU"
    assert b._use_kline is False, "must not keep the failed attempt's K-line profile"
    # The restored virtual ECU still works on the right protocol profile.
    assert b.read_dtcs() == []
    b.disconnect()


def test_failed_ble_attempt_rolls_back_kind_and_profile(monkeypatch):
    """Same rollback for BLE. The transport is stubbed out so the test neither
    scans for real Bluetooth devices (~12 s) nor needs a BLE radio present."""
    monkeypatch.setattr(
        "gems_t4.app.backend.BleTransport", lambda *a, **kw: _FailingTransport()
    )
    b = Backend()
    b.connect()

    try:
        b.apply_connection("ble", device="no-such-pico-xyz")
    except Exception:
        pass
    else:  # pragma: no cover - the stub always fails
        raise AssertionError("expected the stubbed BLE transport to fail")

    assert b.connection_kind == "virtual"
    assert b._use_kline is False
    assert b.read_dtcs() == []
    b.disconnect()
