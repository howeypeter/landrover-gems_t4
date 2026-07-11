"""TCP transport + frame server — full-stack integration over a real socket.

Spins a :class:`TcpFrameServer` (virtual ECU behind it) on an ephemeral
localhost port in a background thread, then drives it through
``KwpClient(TcpTransport(...))`` exactly the way the CLI/GUI ``--connect``
path does. Also covers the wireless write gate and endpoint parsing.
"""
from __future__ import annotations

import socket
import threading
import time

import pytest

from gems_t4.app.server import TcpFrameServer, run_serial_bridge
from gems_t4.gems import actuators, dtc, immobiliser, livedata
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient, WirelessWriteRefused
from gems_t4.protocol.security import compute_key
from gems_t4.transport.base import TransportError, TransportTimeout
from gems_t4.transport.pico import encode_host
from gems_t4.transport.tcp import DEFAULT_PORT, TcpTransport, parse_endpoint
from gems_t4.transport.virtual import VirtualTransport


@pytest.fixture
def served_ecu(request):
    """Start a frame server over a virtual ECU; yield (host, port, ecu)."""

    def start(scenario: str = "healthy", **ecu_kwargs):
        ecu = VirtualEcu(get_scenario(scenario), **ecu_kwargs)
        server = TcpFrameServer(
            VirtualTransport(ecu), port=0, on_exchange=ecu.tick
        )
        server.start_background()
        request.addfinalizer(server.stop)
        host, port = server.address
        return host, port, ecu

    return start


def _client(host: str, port: int, **kwargs) -> KwpClient:
    return KwpClient(TcpTransport(host, port, timeout=5.0, **kwargs))


# -- plumbing ---------------------------------------------------------------- #

def test_ping_reports_server_version(served_ecu):
    host, port, _ = served_ecu()
    transport = TcpTransport(host, port)
    transport.open()
    try:
        assert transport.ping().startswith(b"gems_t4 serve")
    finally:
        transport.close()


def test_connect_and_session_over_tcp(served_ecu):
    host, port, _ = served_ecu()
    client = _client(host, port)
    result = client.connect()
    try:
        assert result.keybytes == b"\x08\x08"
        client.start_session()
        client.tester_present()
    finally:
        client.close()


def test_open_fails_cleanly_when_nothing_listens():
    # Bind-then-close guarantees a port with no listener.
    import socket

    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    dead_port = probe.getsockname()[1]
    probe.close()
    with pytest.raises(TransportError):
        TcpTransport("127.0.0.1", dead_port, timeout=1.0).open()


# -- diagnostics over the wire ------------------------------------------------#

def test_dtc_read_matches_scenario(served_ecu):
    host, port, _ = served_ecu("misfire_cyl3")
    with _client(host, port) as client:
        client.start_session()
        codes = {d.code for d in dtc.read_dtcs(client)}
    assert "P0303" in codes


def test_healthy_scenario_has_no_dtcs_and_clear_is_allowed(served_ecu):
    host, port, _ = served_ecu()
    with _client(host, port) as client:
        client.start_session()
        assert dtc.read_dtcs(client) == []
        # Clear is part of the monitoring workflow — allowed over network.
        dtc.clear_dtcs(client)


def test_live_data_over_tcp(served_ecu):
    host, port, _ = served_ecu()
    with _client(host, port) as client:
        client.start_session()
        measures = livedata.read_all(client)
    assert len(measures) >= 30
    names = {m.name for m in measures}
    assert any("RPM" in n or "speed" in n.lower() or "Engine" in n for n in names)


def test_server_ticks_simulation_between_exchanges(request):
    """Remote clients rely on the SERVER advancing the warm-up sim: the
    on_exchange hook must fire with a wall-clock dt for every exchange after
    the first."""
    ecu = VirtualEcu(get_scenario("healthy"))
    ticks: list[float] = []
    server = TcpFrameServer(
        VirtualTransport(ecu), port=0, on_exchange=ticks.append
    )
    server.start_background()
    request.addfinalizer(server.stop)
    host, port = server.address
    with _client(host, port) as client:
        client.start_session()
        dtc.read_dtcs(client)
        dtc.read_dtcs(client)
    assert len(ticks) >= 2  # session + reads, minus the dt-less first exchange
    assert all(dt >= 0 for dt in ticks)


# -- the wireless write gate ---------------------------------------------------#

def test_writes_refused_over_network_by_default(served_ecu):
    host, port, _ = served_ecu()
    with _client(host, port) as client:
        client.start_session()
        with pytest.raises(WirelessWriteRefused):
            client.actuator(actuators.ACT_MIL, actuators.STATE_ON)
        with pytest.raises(WirelessWriteRefused):
            client.write_data_by_local_id(0x90, b"ABC123")
        # The $31 LEARN routines are writes — blocked...
        with pytest.raises(WirelessWriteRefused):
            client.start_routine(immobiliser.ROUTINE_ENTER_LEARN)
        with pytest.raises(WirelessWriteRefused):
            client.start_routine(immobiliser.ROUTINE_SUBMIT_CODE, b"\xa5\xa5")
        # ...and $27 SecurityAccess mutates ECU security state — blocked too.
        with pytest.raises(WirelessWriteRefused):
            client.security_access(compute_key)
        # But the $31 STATUS routine is a pure read — allowed.
        status = immobiliser.read_status(client)
        assert status.mobilised
        # Ordinary reads still work on the same session.
        assert dtc.read_dtcs(client) == []


def test_security_learn_fails_cleanly_over_readonly_network(served_ecu):
    """security_learn must return its documented result object (not raise) and
    must not have unlocked the remote ECU before being refused."""
    host, port, ecu = served_ecu()
    with _client(host, port) as client:
        client.start_session()
        result = immobiliser.security_learn(client)
    assert not result.ok
    assert not ecu._unlocked  # the $27 unlock never reached the ECU


def test_allow_writes_opt_in_unblocks_actuators(served_ecu):
    host, port, _ = served_ecu()
    with _client(host, port, allow_writes=True) as client:
        client.start_session()
        outcome = actuators.run(client, actuators.ACT_MIL, actuators.STATE_ON)
    assert outcome.ok


def test_usb_and_virtual_paths_unaffected_by_gate():
    """The gate keys off is_wireless — wired/virtual transports never trip it."""
    ecu = VirtualEcu(get_scenario("healthy"))
    client = KwpClient(VirtualTransport(ecu))
    client.connect()
    client.start_session()
    outcome = actuators.run(client, actuators.ACT_MIL, actuators.STATE_ON)
    assert outcome.ok
    client.close()


# -- server robustness (hostile/malformed input must never kill it) -----------#

def test_server_survives_malformed_input(served_ecu):
    """Garbage bytes, bad CRCs, unknown commands and un-parseable KWP payloads
    must each get an error status (or be resynced past) — and the server must
    still answer a healthy client afterwards."""
    host, port, _ = served_ecu()
    raw = socket.create_connection((host, port), timeout=5.0)
    raw.settimeout(5.0)
    try:
        # 1. A valid host frame whose KWP payload is garbage (1 byte): the
        #    documented server-killer. Expect a status reply, not silence.
        raw.sendall(encode_host(0x03, b"\x00"))
        reply = raw.recv(64)
        assert reply and reply[0] == 0x5A
        assert reply[1] != 0x00  # some error status, never OK

        # 2. Leading garbage then a valid PING — resync must find the frame.
        raw.sendall(b"\xde\xad\xbe\xef" + encode_host(0x01))
        reply = raw.recv(64)
        assert reply[0] == 0x5A and reply[1] == 0x00  # PING OK

        # 3. A frame with a corrupted CRC -> BAD_REQUEST (0x03).
        bad = bytearray(encode_host(0x01))
        bad[-1] ^= 0xFF
        raw.sendall(bytes(bad))
        reply = raw.recv(64)
        assert reply[0] == 0x5A and reply[1] == 0x03

        # 4. An unknown command -> BAD_REQUEST.
        raw.sendall(encode_host(0x7E))
        reply = raw.recv(64)
        assert reply[0] == 0x5A and reply[1] == 0x03
    finally:
        raw.close()

    # 5. The server is still alive and serves a fresh, healthy client.
    with _client(host, port) as client:
        client.start_session()
        assert dtc.read_dtcs(client) == []


def test_server_accepts_sequential_clients(served_ecu):
    """Disconnect/reconnect (every GUI re-apply does this) must re-accept."""
    host, port, _ = served_ecu()
    for _round in range(3):
        with _client(host, port) as client:
            client.start_session()
            assert dtc.read_dtcs(client) == []


def test_server_parity_with_pico_firmware(served_ecu):
    """Byte-level parity with pico_kline.ino for edge frames: truncated
    SET_TIMING -> BAD_REQUEST; short INIT -> BAD_REQUEST."""
    host, port, _ = served_ecu()
    raw = socket.create_connection((host, port), timeout=5.0)
    raw.settimeout(5.0)
    try:
        raw.sendall(encode_host(0x04, b"\x00\x0a"))  # SET_TIMING len 2 (<8)
        assert raw.recv(64)[1] == 0x03  # BAD_REQUEST, like the firmware
        raw.sendall(encode_host(0x04, bytes(8)))  # full-length SET_TIMING
        assert raw.recv(64)[1] == 0x00  # OK
        raw.sendall(encode_host(0x02, b"\x10"))  # INIT with 1-byte payload
        assert raw.recv(64)[1] == 0x03  # BAD_REQUEST, like the firmware
    finally:
        raw.close()


def test_transport_resyncs_after_late_reply(request):
    """A reply that arrives after the client timed out must be drained, not
    read as the answer to the NEXT request (the off-by-one desync)."""
    ecu = VirtualEcu(get_scenario("healthy"))
    server = TcpFrameServer(
        VirtualTransport(ecu, latency=0.8), port=0, on_exchange=ecu.tick
    )
    server.start_background()
    request.addfinalizer(server.stop)
    host, port = server.address
    transport = TcpTransport(host, port, timeout=0.2)
    client = KwpClient(transport)
    client.connect()  # INIT is instant (latency applies to SEND_RECV only)
    try:
        with pytest.raises(TransportError):
            client.start_session()  # server answers ~0.8s late -> timeout
        time.sleep(1.5)  # let the stale reply land in the socket buffer
        # Widen the timeout so the retry can succeed; it must drain the stale
        # reply first and pair with ITS OWN response — pre-fix, this raised
        # FramingError/ProtocolError from reading the stale frame.
        transport._timeout = 5.0
        resp = client.start_session()
        assert not resp.is_negative
    finally:
        client.close()


# -- serial bridge (fake serial object) ----------------------------------------#

class _LoopbackSerial:
    """Fake serial handle: echoes written bytes back, prefixed, on read()."""

    def __init__(self) -> None:
        self._buf = bytearray()
        self._lock = threading.Lock()
        self.closed = False

    def write(self, data: bytes) -> int:
        with self._lock:
            self._buf.extend(b"pico:" + bytes(data))
        return len(data)

    def read(self, n: int) -> bytes:
        with self._lock:
            out = bytes(self._buf[:n])
            del self._buf[:n]
        if not out:
            time.sleep(0.01)  # emulate the 50 ms serial read timeout
        return out

    def close(self) -> None:
        self.closed = True


def test_serial_bridge_round_trip():
    """Bytes from a TCP client reach the (fake) serial port and its replies
    come back — and stop_event actually stops the bridge."""
    fake = _LoopbackSerial()
    stop = threading.Event()
    ready: list[int] = []

    def log(msg: str) -> None:
        if msg.startswith("bridging"):
            ready.append(int(msg.rsplit(":", 1)[1]))

    t = threading.Thread(
        target=run_serial_bridge,
        args=("FAKE0",),
        kwargs={
            "port": 0,
            "log": log,
            "stop_event": stop,
            "serial_factory": lambda: fake,
        },
        daemon=True,
    )
    t.start()
    deadline = time.monotonic() + 5.0
    while not ready and time.monotonic() < deadline:
        time.sleep(0.01)
    assert ready, "bridge never reported its port"

    conn = socket.create_connection(("127.0.0.1", ready[0]), timeout=5.0)
    conn.settimeout(5.0)
    try:
        conn.sendall(b"\xa5\x01\x00\x01")
        got = b""
        while len(got) < 9:
            got += conn.recv(64)
        assert got == b"pico:\xa5\x01\x00\x01"
    finally:
        conn.close()
    stop.set()
    t.join(timeout=5.0)
    assert not t.is_alive()
    assert fake.closed


# -- endpoint parsing -----------------------------------------------------------#

def test_parse_endpoint_forms():
    assert parse_endpoint("192.168.1.50") == ("192.168.1.50", DEFAULT_PORT)
    assert parse_endpoint("192.168.1.50:5000") == ("192.168.1.50", 5000)
    assert parse_endpoint("pi.local:9141") == ("pi.local", 9141)
    with pytest.raises(ValueError):
        parse_endpoint(":9141")
    with pytest.raises(ValueError):
        parse_endpoint("host:notaport")
    with pytest.raises(ValueError):
        parse_endpoint("host:99999")


def test_parse_endpoint_ipv6_forms():
    assert parse_endpoint("::1") == ("::1", DEFAULT_PORT)
    assert parse_endpoint("fe80::5") == ("fe80::5", DEFAULT_PORT)
    assert parse_endpoint("[::1]") == ("::1", DEFAULT_PORT)
    assert parse_endpoint("[::1]:5000") == ("::1", 5000)
    with pytest.raises(ValueError):
        parse_endpoint("[::1")  # unclosed bracket
    with pytest.raises(ValueError):
        parse_endpoint("[::1]junk")
