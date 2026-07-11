"""TCP transport — the Pico host protocol over a network socket.

``TcpTransport`` speaks exactly the same length-prefixed host protocol as
:class:`~gems_t4.transport.pico.PicoAdapterTransport` (see
``firmware/HOST_PROTOCOL.md``), but over TCP instead of USB-CDC serial. The far
end of the socket can be:

* ``gems_t4 serve`` — the virtual ECU served over TCP (test bench), or the
  same command bridging a USB Pico on another machine (e.g. a Raspberry Pi
  at the car), or
* a future Pico 2 W running WiFi firmware, answering directly.

The laptop-side code cannot tell these apart — that is the point.

Network transports are treated as *wireless* for the write policy: coding
writes, actuator commands and Security-Learn are refused by
:class:`~gems_t4.protocol.client.KwpClient` unless ``allow_writes=True`` is
passed explicitly (CLAUDE.md: writes stay wired-only by default).
"""
from __future__ import annotations

import socket

from gems_t4.transport.base import (
    InitError,
    InitResult,
    Transport,
    TransportClosed,
    TransportError,
    TransportTimeout,
)
from gems_t4.transport.pico import (
    CMD_INIT,
    CMD_PING,
    CMD_SEND_RECV,
    PICO_START,
    STATUS_OK,
    STATUS_TIMEOUT,
    decode_pico,
    encode_host,
)

_MODE_CODE = {"slow": 0, "fast": 1}

#: Default TCP port for the gems_t4 frame service (mnemonic for ISO 9141).
DEFAULT_PORT = 9141

#: Socket timeout for the INIT exchange. A real 5-baud slow init takes several
#: seconds on the far side (2+ s of address bits alone), so INIT gets a much
#: longer deadline than an ordinary request/response.
INIT_TIMEOUT = 15.0


class TcpTransport(Transport):
    """Talk the Pico host protocol to a TCP endpoint (bridge or WiFi Pico)."""

    #: Network paths are read-only unless explicitly opted in — see module doc.
    is_wireless = True

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        *,
        timeout: float = 5.0,
        allow_writes: bool = False,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        #: Read by KwpClient's wireless write gate; True permits write services.
        self.allow_writes = allow_writes
        self._sock: socket.socket | None = None
        self._pending: bytes | None = None
        #: Set when an exchange aborted mid-read (timeout / bad byte): a late
        #: reply may still land in the socket buffer, and reading it as the
        #: answer to the NEXT request would desynchronize every exchange after.
        self._dirty = False

    # -- lifecycle ---------------------------------------------------------- #
    def open(self) -> None:
        if self._sock is not None:
            return
        try:
            sock = socket.create_connection(
                (self._host, self._port), timeout=self._timeout
            )
        except OSError as exc:
            raise TransportError(
                f"cannot connect to {self._host}:{self._port}: {exc}"
            ) from exc
        # Frames are tiny and strictly request/response; don't let Nagle batch
        # them behind delayed ACKs.
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.settimeout(self._timeout)
        self._sock = sock

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:  # pragma: no cover - best-effort close
                pass
            self._sock = None
        self._pending = None
        self._dirty = False

    def is_open(self) -> bool:
        return self._sock is not None

    # -- socket helpers ------------------------------------------------------ #
    def _read_exact(self, n: int) -> bytes:
        """Read exactly ``n`` bytes, or raise on timeout / peer close."""
        assert self._sock is not None
        buf = bytearray()
        while len(buf) < n:
            try:
                chunk = self._sock.recv(n - len(buf))
            except socket.timeout as exc:
                raise TransportTimeout(
                    f"no response from {self._host}:{self._port}"
                ) from exc
            except OSError as exc:
                raise TransportError(f"socket error: {exc}") from exc
            if not chunk:
                raise TransportError(
                    f"connection closed by {self._host}:{self._port}"
                )
            buf.extend(chunk)
        return bytes(buf)

    def _drain_stale(self) -> None:
        """Discard any late bytes left over from an aborted exchange.

        The protocol is strictly request/response, so after a timed-out read
        anything sitting in the receive buffer is a stale reply to an old
        request — swallow it before sending the next one, or every later
        exchange would answer the previous request (permanent off-by-one).
        """
        assert self._sock is not None
        self._sock.setblocking(False)
        try:
            while True:
                try:
                    if not self._sock.recv(4096):
                        break  # peer closed; the next send will surface it
                except BlockingIOError:
                    break
                except OSError:
                    break
        finally:
            self._sock.settimeout(self._timeout)
        self._dirty = False

    def _transceive(
        self, cmd: int, payload: bytes = b"", *, timeout: float | None = None
    ) -> tuple[int, bytes]:
        """One host-protocol exchange: send a command frame, read the reply."""
        if self._sock is None:
            raise TransportClosed("transport is not open")
        if self._dirty:
            self._drain_stale()
        self._sock.settimeout(timeout if timeout is not None else self._timeout)
        try:
            self._sock.sendall(encode_host(cmd, payload))
        except OSError as exc:
            raise TransportError(f"socket send failed: {exc}") from exc
        self._dirty = True  # cleared below once a full reply is consumed
        start = self._read_exact(1)
        if start[0] != PICO_START:
            raise TransportError(f"unexpected byte 0x{start[0]:02X} from server")
        header = self._read_exact(2)
        status, length = header[0], header[1]
        payload_in = self._read_exact(length) if length else b""
        crc_in = self._read_exact(1)
        self._dirty = False
        frame = bytes([PICO_START, status, length]) + payload_in + crc_in
        return decode_pico(frame)

    # -- Transport interface ------------------------------------------------ #
    def ping(self) -> bytes:
        """PING the far end; returns its version payload."""
        status, payload = self._transceive(CMD_PING)
        if status != STATUS_OK:
            raise TransportError(f"PING failed (status {status})")
        return payload

    def init(self, address: int, mode: str = "slow") -> InitResult:
        code = _MODE_CODE.get(mode)
        if code is None:
            raise ValueError(f"unknown init mode {mode!r}")
        status, payload = self._transceive(
            CMD_INIT, bytes([address, code]), timeout=INIT_TIMEOUT
        )
        if status != STATUS_OK:
            raise InitError(f"init failed (status {status})")
        return InitResult(keybytes=bytes(payload))

    def send(self, frame: bytes) -> None:
        status, payload = self._transceive(CMD_SEND_RECV, frame)
        if status == STATUS_TIMEOUT:
            raise TransportTimeout("K-line response timed out")
        if status != STATUS_OK:
            raise TransportError(f"bus error (status {status})")
        self._pending = payload

    def receive(self, timeout: float | None = None) -> bytes:
        if self._pending is None:
            raise TransportTimeout("no buffered response")
        frame = self._pending
        self._pending = None
        return frame


def parse_endpoint(value: str) -> tuple[str, int]:
    """Parse a ``HOST[:PORT]`` string (e.g. from ``--connect``).

    The port defaults to :data:`DEFAULT_PORT`. IPv6 literals are supported
    bracketed with a port (``[::1]:9141``) or bare without one (``::1`` —
    more than one colon means the whole value is the host).
    """
    if value.startswith("["):  # bracketed IPv6: [addr] or [addr]:port
        addr, sep, rest = value[1:].partition("]")
        if not sep or not addr:
            raise ValueError(f"invalid endpoint {value!r}: unclosed '['")
        if not rest:
            return addr, DEFAULT_PORT
        if not rest.startswith(":"):
            raise ValueError(f"invalid endpoint {value!r}: junk after ']'")
        return addr, _parse_port(value, rest[1:])
    if value.count(":") > 1:  # bare IPv6 literal, no port
        return value, DEFAULT_PORT
    host, sep, port_s = value.rpartition(":")
    if not sep:
        return value, DEFAULT_PORT
    if not host:
        raise ValueError(f"invalid endpoint {value!r}: empty host")
    return host, _parse_port(value, port_s)


def _parse_port(value: str, port_s: str) -> int:
    try:
        port = int(port_s)
    except ValueError as exc:
        raise ValueError(f"invalid endpoint {value!r}: bad port") from exc
    if not 0 < port < 65536:
        raise ValueError(f"invalid endpoint {value!r}: port out of range")
    return port
