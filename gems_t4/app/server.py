"""``gems_t4 serve`` — the network end of the TCP transport.

Two modes, both answering :class:`~gems_t4.transport.tcp.TcpTransport` clients
with the exact host protocol a Pico speaks over USB (``firmware/
HOST_PROTOCOL.md``):

* **Virtual** (default): :class:`TcpFrameServer` decodes each host-protocol
  command and answers from a local :class:`~gems_t4.transport.base.Transport`
  (the in-memory virtual ECU). Because the client's local simulation ``tick()``
  is a no-op in remote mode, the server advances the ECU simulation by
  wall-clock time between exchanges.
* **Serial bridge** (``--port COMx``): :func:`run_serial_bridge` is a dumb byte
  passthrough between the TCP client and a USB Pico adapter — the remote
  client is effectively talking straight to the Pico, timing quirks and all.

One client at a time, mirroring the one-tester-per-K-line reality. Binds to
127.0.0.1 by default; pass ``--listen 0.0.0.0:9141`` to expose on the LAN (or
keep localhost and reach it through an SSH tunnel, which adds auth+encryption).
"""
from __future__ import annotations

import socket
import threading
import time
from typing import Callable

from gems_t4 import __version__
from gems_t4.transport.base import (
    InitError,
    Transport,
    TransportError,
    TransportTimeout,
)
from gems_t4.transport.pico import (
    CMD_INIT,
    CMD_PING,
    CMD_SEND_RECV,
    CMD_SET_TIMING,
    HOST_START,
    PICO_START,
    STATUS_BAD_REQUEST,
    STATUS_BUS_ERROR,
    STATUS_OK,
    STATUS_TIMEOUT,
    crc8,
)
from gems_t4.transport.tcp import DEFAULT_PORT


def encode_reply(status: int, payload: bytes = b"") -> bytes:
    """Build a server->client (Pico->host direction) frame."""
    if len(payload) > 0xFF:
        raise ValueError("payload too long for one frame")
    body = bytes([status, len(payload)]) + payload
    return bytes([PICO_START]) + body + bytes([crc8(body)])


class TcpFrameServer:
    """Serve the host protocol over TCP, answering from a local transport.

    Parameters
    ----------
    transport:
        The local :class:`Transport` that actually answers (normally a
        :class:`~gems_t4.transport.virtual.VirtualTransport` over a
        :class:`~gems_t4.gems.virtual_ecu.VirtualEcu`).
    host / port:
        Listen address. ``port=0`` picks an ephemeral port (tests); the bound
        address is available as :attr:`address` after construction.
    on_exchange:
        Optional ``f(dt_seconds)`` called before each SEND_RECV with the
        wall-clock time since the previous one — wire the virtual ECU's
        ``tick`` here so warm-up/idle simulation advances for remote clients.
    """

    def __init__(
        self,
        transport: Transport,
        *,
        host: str = "127.0.0.1",
        port: int = DEFAULT_PORT,
        on_exchange: Callable[[float], None] | None = None,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._transport = transport
        self._on_exchange = on_exchange
        self._log = log or (lambda msg: None)
        self._stopping = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_exchange: float | None = None

        self._listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._listener.bind((host, port))
        self._listener.listen(1)
        self._listener.settimeout(0.5)  # so serve_forever can notice stop()
        #: The actually-bound (host, port) — useful when ``port=0``.
        self.address: tuple[str, int] = self._listener.getsockname()[:2]

    # -- lifecycle ----------------------------------------------------------- #
    def serve_forever(self) -> None:
        """Accept and serve one client at a time until :meth:`stop`."""
        try:
            while not self._stopping.is_set():
                try:
                    conn, peer = self._listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break  # listener closed by stop()
                with conn:
                    self._log(f"client connected: {peer[0]}:{peer[1]}")
                    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    conn.settimeout(0.5)
                    self._serve_client(conn)
                    self._log("client disconnected")
        finally:
            self._listener.close()

    def start_background(self) -> threading.Thread:
        """Run :meth:`serve_forever` on a daemon thread (tests / GUI-side use)."""
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        self._thread = thread
        return thread

    def stop(self) -> None:
        """Stop accepting and unwind. Safe to call more than once."""
        self._stopping.set()
        try:
            self._listener.close()
        except OSError:  # pragma: no cover - best-effort close
            pass
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    # -- per-client loop ------------------------------------------------------#
    def _serve_client(self, conn: socket.socket) -> None:
        while not self._stopping.is_set():
            frame = self._read_host_frame(conn)
            if frame is None:
                return  # client closed
            try:
                reply = self._handle(frame)
            except Exception as exc:  # noqa: BLE001 - a hostile/buggy client
                # must never kill the server (a real Pico can't crash either);
                # e.g. FramingError from a malformed KWP payload.
                self._log(f"exchange error: {exc}")
                reply = encode_reply(STATUS_BUS_ERROR)
            try:
                conn.sendall(reply)
            except OSError:
                return

    def _read_host_frame(self, conn: socket.socket) -> bytes | None:
        """Read one complete host frame; None when the client disconnects."""

        def read_exact(n: int) -> bytes | None:
            buf = bytearray()
            while len(buf) < n:
                if self._stopping.is_set():
                    return None
                try:
                    chunk = conn.recv(n - len(buf))
                except socket.timeout:
                    continue
                except OSError:
                    return None
                if not chunk:
                    return None
                buf.extend(chunk)
            return bytes(buf)

        # Resync: skip bytes until the start marker.
        while True:
            b = read_exact(1)
            if b is None:
                return None
            if b[0] == HOST_START:
                break
        header = read_exact(2)
        if header is None:
            return None
        cmd, length = header[0], header[1]
        rest = read_exact(length + 1)  # payload + crc
        if rest is None:
            return None
        return bytes([HOST_START, cmd, length]) + rest

    def _handle(self, frame: bytes) -> bytes:
        """Dispatch one validated host frame to the local transport."""
        cmd, length = frame[1], frame[2]
        payload = frame[3 : 3 + length]
        if frame[3 + length] != crc8(frame[1 : 3 + length]):
            return encode_reply(STATUS_BAD_REQUEST)

        if cmd == CMD_PING:
            return encode_reply(
                STATUS_OK, f"gems_t4 serve {__version__}".encode("ascii")
            )

        if cmd == CMD_INIT:
            # Mirror the Pico firmware exactly (pico_kline.ino handleInit):
            # len < 2 -> BAD_REQUEST; mode 1 = fast, anything else = slow;
            # a failed init answers TIMEOUT, not BUS_ERROR.
            if len(payload) < 2:
                return encode_reply(STATUS_BAD_REQUEST)
            mode = "fast" if payload[1] == 1 else "slow"
            try:
                result = self._transport.init(payload[0], mode)
            except (InitError, TransportError):
                return encode_reply(STATUS_TIMEOUT)
            return encode_reply(STATUS_OK, result.keybytes)

        if cmd == CMD_SEND_RECV:
            self._tick()
            try:
                self._transport.send(payload)
                response = self._transport.receive()
            except TransportTimeout:
                return encode_reply(STATUS_TIMEOUT)
            except TransportError:
                return encode_reply(STATUS_BUS_ERROR)
            return encode_reply(STATUS_OK, response)

        if cmd == CMD_SET_TIMING:
            # No K-line of our own to retime, but validate like the firmware
            # does (pico_kline.ino handleSetTiming: len < 8 -> BAD_REQUEST).
            if len(payload) < 8:
                return encode_reply(STATUS_BAD_REQUEST)
            return encode_reply(STATUS_OK)

        return encode_reply(STATUS_BAD_REQUEST)

    def _tick(self) -> None:
        """Advance the simulation by wall-clock time since the last exchange."""
        now = time.monotonic()
        if self._on_exchange is not None and self._last_exchange is not None:
            self._on_exchange(now - self._last_exchange)
        self._last_exchange = now


def run_serial_bridge(
    serial_port: str,
    *,
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    log: Callable[[str], None] | None = None,
    baud: int = 115200,
    stop_event: threading.Event | None = None,
    serial_factory: Callable[[], object] | None = None,
) -> None:
    """Raw byte passthrough: TCP client <-> USB Pico adapter on ``serial_port``.

    The remote :class:`TcpTransport` talks straight to the Pico firmware —
    no decode/re-encode, perfect protocol fidelity (SET_TIMING included).
    One client at a time; runs until KeyboardInterrupt (or ``stop_event``).

    A serial error (adapter unplugged mid-session, port won't open) drops the
    current client and goes back to accepting — the bridge itself must survive
    anything the hardware does. ``serial_factory`` injects a fake serial object
    for tests, mirroring PicoAdapterTransport's ``serial_obj`` seam.
    """
    if serial_factory is None:
        try:
            import serial  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover - env-dependent
            raise TransportError(
                "pyserial is required for the serial bridge"
            ) from exc

        def serial_factory() -> object:
            return serial.Serial(serial_port, baud, timeout=0.05)

    emit = log or (lambda msg: None)
    stop = stop_event or threading.Event()
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(1)
    # A blocking accept() swallows Ctrl+C on Windows — poll so both
    # KeyboardInterrupt and stop_event get a chance.
    listener.settimeout(0.5)
    emit(f"bridging {serial_port} on {host}:{listener.getsockname()[1]}")
    try:
        while not stop.is_set():
            try:
                conn, peer = listener.accept()
            except socket.timeout:
                continue
            emit(f"client connected: {peer[0]}:{peer[1]}")
            try:
                with conn:
                    _bridge_one_client(conn, serial_factory, stop, emit)
            except OSError as exc:  # incl. serial.SerialException
                emit(f"serial error, dropping client: {exc}")
                continue
            emit("client disconnected")
    finally:
        listener.close()


def _bridge_one_client(
    conn: socket.socket,
    serial_factory: Callable[[], object],
    stop: threading.Event,
    emit: Callable[[str], None],
) -> None:
    """Pump bytes both ways between one TCP client and a fresh serial handle.

    Raises OSError (which includes pyserial's SerialException) if the serial
    side fails — the caller drops the client and keeps the bridge alive.
    """
    ser = serial_factory()  # fresh handle per client: re-plugging the adapter
    try:  # between sessions just works
        conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        conn.settimeout(0.05)
        client_stop = threading.Event()
        pump_error: list[BaseException] = []

        def pump_serial_to_tcp() -> None:
            while not (client_stop.is_set() or stop.is_set()):
                try:
                    data = ser.read(256)
                except Exception as exc:  # noqa: BLE001 - serial died
                    pump_error.append(exc)
                    try:  # unblock the recv loop so the error surfaces
                        conn.shutdown(socket.SHUT_RDWR)
                    except OSError:
                        pass
                    return
                if data:
                    try:
                        conn.sendall(data)
                    except OSError:
                        return

        t = threading.Thread(target=pump_serial_to_tcp, daemon=True)
        t.start()
        try:
            while not stop.is_set():
                try:
                    data = conn.recv(256)
                except socket.timeout:
                    continue
                except OSError:
                    break
                if not data:
                    break
                ser.write(data)
        finally:
            client_stop.set()
            t.join(timeout=2.0)
        if pump_error:
            raise OSError(f"serial read failed: {pump_error[0]}")
    finally:
        try:
            ser.close()
        except Exception:  # noqa: BLE001 - best-effort close
            pass
