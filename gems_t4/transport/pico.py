"""USB-CDC transport to the Pico smart adapter.

The Pico owns the K-line timing; this class just ferries complete KWP frames to
it over the host protocol defined in ``firmware/HOST_PROTOCOL.md`` and mirrored
here:

    Host->Pico:  0xA5 <cmd>    <len> <payload...> <crc8>
    Pico->Host:  0x5A <status> <len> <payload...> <crc8>

``crc8`` = XOR of the ``cmd``/``status`` byte, the ``len`` byte, and every
payload byte. Commands: 0x01 PING, 0x02 INIT [addr][mode], 0x03 SEND_RECV
[kwp frame], 0x04 SET_TIMING [P1..P4 as 4x uint16 ms]. Status: 0x00 OK,
0x01 TIMEOUT, 0x02 BUS_ERROR, 0x03 BAD_REQUEST.

The serial object is injectable so the host-protocol framing is unit-testable
without hardware.
"""
from __future__ import annotations

from functools import reduce
from typing import Any

from gems_t4.transport.base import (
    InitError,
    InitResult,
    Transport,
    TransportClosed,
    TransportError,
    TransportTimeout,
)

HOST_START = 0xA5
PICO_START = 0x5A

CMD_PING = 0x01
CMD_INIT = 0x02
CMD_SEND_RECV = 0x03
CMD_SET_TIMING = 0x04

STATUS_OK = 0x00
STATUS_TIMEOUT = 0x01
STATUS_BUS_ERROR = 0x02
STATUS_BAD_REQUEST = 0x03

_MODE_CODE = {"slow": 0, "fast": 1}


def crc8(body: bytes) -> int:
    """XOR checksum over ``body`` (the cmd/status byte, len byte, and payload)."""
    return reduce(lambda a, b: a ^ b, body, 0)


def encode_host(cmd: int, payload: bytes = b"") -> bytes:
    """Build a host->Pico frame."""
    if len(payload) > 0xFF:
        raise ValueError("payload too long for one host frame")
    body = bytes([cmd, len(payload)]) + payload
    return bytes([HOST_START]) + body + bytes([crc8(body)])


def decode_pico(frame: bytes) -> tuple[int, bytes]:
    """Parse a complete Pico->host frame into ``(status, payload)``."""
    if len(frame) < 4:
        raise TransportError(f"pico frame too short: {len(frame)} bytes")
    if frame[0] != PICO_START:
        raise TransportError(f"bad pico start byte 0x{frame[0]:02X}")
    status, length = frame[1], frame[2]
    payload = frame[3 : 3 + length]
    if len(payload) != length:
        raise TransportError("pico frame truncated")
    expected = crc8(frame[1 : 3 + length])
    if frame[3 + length] != expected:
        raise TransportError("pico frame crc mismatch")
    return status, payload


class PicoAdapterTransport(Transport):
    """Talk to the Pico K-line adapter over USB-CDC serial."""

    def __init__(
        self,
        port: str | None = None,
        *,
        serial_obj: Any | None = None,
        baud: int = 115200,
        timeout: float = 2.0,
    ) -> None:
        self._port = port
        self._serial = serial_obj
        self._baud = baud
        self._timeout = timeout
        self._injected = serial_obj is not None
        self._open = self._injected
        self._pending: bytes | None = None

    # -- lifecycle ---------------------------------------------------------- #
    def open(self) -> None:
        if self._serial is None:
            try:
                import serial  # type: ignore
            except ModuleNotFoundError as exc:  # pragma: no cover
                raise TransportError(
                    "pyserial is required for PicoAdapterTransport"
                ) from exc
            if self._port is None:
                raise TransportError("no serial port specified")
            self._serial = serial.Serial(self._port, self._baud, timeout=self._timeout)
        self._open = True

    def close(self) -> None:
        if self._serial is not None and not self._injected:
            try:
                self._serial.close()
            except Exception:  # pragma: no cover - best-effort close
                pass
            self._serial = None
        self._open = False

    def is_open(self) -> bool:
        return self._open

    # -- host-protocol exchange -------------------------------------------- #
    def _transceive(self, cmd: int, payload: bytes = b"") -> tuple[int, bytes]:
        if not self._open or self._serial is None:
            raise TransportClosed("transport is not open")
        self._serial.write(encode_host(cmd, payload))
        start = self._serial.read(1)
        if not start:
            raise TransportTimeout("no response from Pico")
        if start[0] != PICO_START:
            raise TransportError(f"unexpected byte 0x{start[0]:02X} from Pico")
        header = self._serial.read(2)
        if len(header) < 2:
            raise TransportTimeout("truncated Pico header")
        status, length = header[0], header[1]
        payload_in = self._serial.read(length) if length else b""
        crc_in = self._serial.read(1)
        frame = bytes([PICO_START, status, length]) + payload_in + bytes(crc_in)
        return decode_pico(frame)

    def ping(self) -> bytes:
        """PING the adapter; returns its version payload."""
        status, payload = self._transceive(CMD_PING)
        if status != STATUS_OK:
            raise TransportError(f"PING failed (status {status})")
        return payload

    def init(self, address: int, mode: str = "slow") -> InitResult:
        code = _MODE_CODE.get(mode)
        if code is None:
            raise ValueError(f"unknown init mode {mode!r}")
        status, payload = self._transceive(CMD_INIT, bytes([address, code]))
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
