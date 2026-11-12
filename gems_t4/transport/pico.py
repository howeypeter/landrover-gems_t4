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
CMD_SET_WIFI = 0x06
CMD_WIFI_STATUS = 0x07
CMD_RAW_XFER = 0x08
CMD_MONITOR_L = 0x09
CMD_SELECT_CHANNEL = 0x0D
CMD_READ_PINS = 0x0E

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


def encode_set_wifi_payload(ssid: str, password: str) -> bytes:
    """Build the CMD_SET_WIFI (0x06) payload: ``[ssid_len][ssid][password]``.

    Single source of truth for the WiFi-cred wire format + limits, shared by
    every transport (USB/BLE/TCP) so ``set_wifi`` behaves identically over each
    link. The creds themselves are stored only on the Pico (LittleFS); the host
    never persists them - this just frames the one write command.
    """
    sb = ssid.encode("utf-8")
    pb = password.encode("utf-8")
    if not sb or len(sb) > 32:
        raise ValueError("SSID must be 1..32 bytes")
    if len(pb) > 63:
        raise ValueError("password must be <= 63 bytes")
    return bytes([len(sb)]) + sb + pb


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
        timeout: float = 6.0,  # must exceed the Pico's ~3.3s 5-baud slow-init blocking time
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

    # -- WiFi credential admin (unified firmware; USB only) ---------------- #
    def set_wifi(self, ssid: str, password: str) -> None:
        """Store WiFi credentials on the Pico (LittleFS) so it can join on the
        next boot - no firmware reflash. Payload: [ssid_len][ssid][password]."""
        status, _ = self._transceive(CMD_SET_WIFI, encode_set_wifi_payload(ssid, password))
        if status != STATUS_OK:
            raise TransportError(
                f"set-wifi failed (status {status}) - is this the unified "
                f"firmware with WiFi enabled?"
            )

    def wifi_status(self) -> str:
        """Ask the Pico for its WiFi state ('connected <ip>' / 'offline …' /
        'no-creds'). Returns the firmware's status string."""
        status, payload = self._transceive(CMD_WIFI_STATUS)
        if status != STATUS_OK:
            raise TransportError(f"wifi-status failed (status {status})")
        return payload.decode("ascii", "replace")

    # -- raw / unmapped access (bypasses ALL protocol gating — see callers) - #
    def raw_xfer(self, payload: bytes) -> bytes:
        """Send ``payload`` at the CURRENT session baud/channel with NO echo
        cancellation: the firmware flushes stale RX, transmits, then collects
        everything received over a fixed ~400 ms window (echo bytes first,
        then any real response) and hands it all back unparsed. The caller is
        responsible for separating echo from response. This is the reverse-
        engineering primitive used by the ``bench/*.py`` probe scripts,
        formalized here so it's reachable from the API/Backend instead of only
        ad-hoc scripts. Requires an already-open, already-initialized link
        (call :meth:`select_channel` first if you need a specific channel).
        """
        status, resp = self._transceive(CMD_RAW_XFER, payload)
        if status != STATUS_OK:
            raise TransportError(f"raw_xfer failed (status {status})")
        return resp

    def monitor_l(self, window_ms: int = 1000) -> bytes:
        """Passively capture digital transitions on the active channel's LO
        (L-line comparator) pin for ``window_ms`` (clamped to 5000 by the
        firmware). Read-only — the L9637D's LI/LO path can only sense, never
        drive. Returns ``[initial_level] + N * [dt_hi][dt_lo]`` microsecond
        deltas between transitions; see firmware CMD_MONITOR_L for the format.
        """
        hi, lo = (window_ms >> 8) & 0xFF, window_ms & 0xFF
        status, resp = self._transceive(CMD_MONITOR_L, bytes([hi, lo]))
        if status != STATUS_OK:
            raise TransportError(f"monitor_l failed (status {status})")
        return resp

    # -- dual K-line channel select (Board 1's second L9637D) --------------- #
    def select_channel(self, channel: int) -> None:
        """Pick which L9637D/UART pair subsequent commands operate on.

        ``channel`` 0 = U2 (Serial1, GP0 TX / GP1 RX, LO on GP2) — the default
        at boot. ``channel`` 1 = U3 (Serial2, GP4 TX / GP5 RX, LO on GP6).
        Sticky on the Pico until changed again; every INIT/SEND_RECV/
        SET_TIMING/RAW_INIT/RAW_XFER/MONITOR_L/CAPTURE call after this uses the
        selected channel. Needs firmware >= pico_kline_all 3.8.0.
        """
        if channel not in (0, 1):
            raise ValueError(f"channel must be 0 or 1, got {channel!r}")
        status, _ = self._transceive(CMD_SELECT_CHANNEL, bytes([channel]))
        if status != STATUS_OK:
            raise TransportError(
                f"select-channel failed (status {status}) - is this firmware "
                f"pico_kline_all >= 3.8.0?"
            )

    def read_pins(self) -> dict[str, bool]:
        """Raw digital level of TX/RX/LO on the active channel (see
        :meth:`select_channel`), bypassing UART byte-framing entirely -- reads
        the pad's instantaneous electrical state via the RP2040's GPIO_IN
        register. Unlike :meth:`raw_xfer` (which decodes/returns serial BYTES
        and so reports nothing when there's no traffic to frame), this reports
        a level even when the K-line is open/idle and no Vs is connected --
        per the L9637D datasheet, RX/LO are specified to show a DEFINED level
        in that condition, which is what makes this useful as a no-12V-needed
        orientation cross-check. Needs firmware >= pico_kline_all 3.9.0.
        """
        status, payload = self._transceive(CMD_READ_PINS)
        if status != STATUS_OK:
            raise TransportError(
                f"read-pins failed (status {status}) - is this firmware "
                f"pico_kline_all >= 3.9.0?"
            )
        if len(payload) < 3:
            raise TransportError(f"read-pins: short reply ({len(payload)} bytes)")
        return {"tx": bool(payload[0]), "rx": bool(payload[1]), "lo": bool(payload[2])}


def find_pico_port() -> "str | None":
    """COM port of a connected Raspberry Pi Pico (USB VID 0x2E8A), or None.

    Used for CLI auto-detect when no --port is given: matches by USB vendor id
    so it finds the Pico whatever COMx Windows assigned. Returns the first match.
    """
    try:
        from serial.tools import list_ports
    except Exception:  # pyserial missing
        return None
    for p in list_ports.comports():
        hwid = (getattr(p, "hwid", "") or "").upper()
        if getattr(p, "vid", None) == 0x2E8A or "2E8A" in hwid:
            return p.device
    return None
