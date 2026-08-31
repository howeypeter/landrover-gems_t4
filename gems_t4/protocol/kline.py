"""ISO 9141-2 / OBD-II profile — the protocol a real NAS GEMS ECU speaks.

Confirmed on hardware (P38 GEMS, 2026-08): 5-baud slow init at address
**0x33**, keybytes **0x08 0x08**, request header **68 6A F1**, response header
**48 6B E8**, 1-byte sum checksum. This is the emissions-compliant OBD-II
subset a NAS GEMS ECU answers over the K-line.

This is deliberately separate from the KWP2000-*stylized* virtual-ECU stack in
:mod:`gems_t4.protocol.framing`: that models the T4/$61 request/response shape,
while this speaks the actual bytes a physical ECU returns. It drives any
:class:`~gems_t4.transport.base.Transport` — the USB Pico adapter on the bench
or on-car, or a TCP bridge — so ``gems_t4 kline ... --port COMx`` works against
a real ECU. (Named for the K-line the data rides on — bench or car — not the
J1962 connector, which the bench doesn't use.)

Scope note: the full *proprietary* GEMS/T4 diagnostics (the ~108 live measures,
actuator drives, coding) ride the **same 68 6A F1 envelope** but use
manufacturer service bytes not yet reverse-engineered. :meth:`KlineClient.raw_service`
is the hook to add them as they are discovered at the bench.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from gems_t4.transport.base import InitResult, Transport, TransportError, TransportTimeout

KLINE_INIT_ADDRESS = 0x33
_REQ_HEADER = bytes([0x68, 0x6A, 0xF1])  # format, target (OBD), source (tester)
_RESP_FMT = 0x48  # first byte of an ECU response header (48 6B <ecu>)

__all__ = [
    "KLINE_INIT_ADDRESS",
    "KlineError",
    "KlineClient",
    "Pid",
    "PIDS",
    "encode_request",
    "decode_response",
    "decode_dtcs",
    "obd_checksum",
]


class KlineError(TransportError):
    """OBD framing / protocol error (bad header, checksum, or short frame)."""


def obd_checksum(data: bytes) -> int:
    """ISO 9141-2 checksum: 8-bit sum of every preceding byte."""
    return sum(data) & 0xFF


def encode_request(payload: bytes) -> bytes:
    """Wrap an OBD service payload (e.g. ``b"\\x01\\x05"``) in a full frame."""
    frame = _REQ_HEADER + payload
    return frame + bytes([obd_checksum(frame)])


def decode_response(frame: bytes) -> bytes:
    """Validate an ECU response frame; return its data (service byte + rest).

    Strips the 3-byte ``48 6B <ecu>`` header and the trailing checksum, so a
    ``48 6B E8 41 05 00 E1`` frame returns ``41 05 00``.
    """
    if len(frame) < 5:
        raise KlineError(f"response too short: {frame.hex()}")
    if frame[0] != _RESP_FMT:
        raise KlineError(f"bad response header 0x{frame[0]:02X}: {frame.hex()}")
    if obd_checksum(frame[:-1]) != frame[-1]:
        raise KlineError(f"checksum mismatch: {frame.hex()}")
    return frame[3:-1]


def decode_dtcs(data: bytes) -> list[str]:
    """Decode 2-byte DTC pairs into P/C/B/U codes (e.g. ``P0303``).

    All-zero padding pairs are skipped. ``data`` is the bytes after the ``0x43``
    (Mode 03) or ``0x47`` (Mode 07) response byte.
    """
    codes: list[str] = []
    for i in range(0, len(data) - 1, 2):
        a, b = data[i], data[i + 1]
        if a == 0 and b == 0:
            continue
        system = "PCBU"[(a >> 6) & 0x3]
        codes.append(f"{system}{(a >> 4) & 0x3}{a & 0xF:X}{b >> 4:X}{b & 0xF:X}")
    return codes


# ---- Mode-01 PID catalog ---------------------------------------------------- #

@dataclass(frozen=True, slots=True)
class Pid:
    """One Mode-01 live-data parameter and how to decode its value bytes."""

    pid: int
    name: str
    unit: str
    decode: Callable[[bytes], float | int | str]


def _temp(d: bytes) -> int:
    return d[0] - 40


def _pct(d: bytes) -> float:
    return round(d[0] * 100 / 255, 1)


def _trim(d: bytes) -> float:
    return round((d[0] - 128) * 100 / 128, 1)


def _rpm(d: bytes) -> float:
    return round((d[0] * 256 + d[1]) / 4)


def _timing(d: bytes) -> float:
    return round((d[0] - 128) / 2, 1)


def _maf(d: bytes) -> float:
    return round((d[0] * 256 + d[1]) / 100, 2)


# Common Mode-01 PIDs with decoders. read_live() only reads the ones the ECU
# reports as supported (via PID 00), so listing extras here is harmless.
PIDS: list[Pid] = [
    Pid(0x04, "Engine load", "%", _pct),
    Pid(0x05, "Coolant temp", "°C", _temp),
    Pid(0x06, "Short fuel trim B1", "%", _trim),
    Pid(0x07, "Long fuel trim B1", "%", _trim),
    Pid(0x0C, "Engine speed", "rpm", _rpm),
    Pid(0x0D, "Vehicle speed", "km/h", lambda d: d[0]),
    Pid(0x0E, "Timing advance", "°", _timing),
    Pid(0x0F, "Intake air temp", "°C", _temp),
    Pid(0x10, "MAF rate", "g/s", _maf),
    Pid(0x11, "Throttle", "%", _pct),
    Pid(0x14, "O2 B1S1 voltage", "V", lambda d: round(d[0] / 200, 3)),
    Pid(0x15, "O2 B1S2 voltage", "V", lambda d: round(d[0] / 200, 3)),
]


@dataclass(slots=True)
class LiveRow:
    """One decoded live-data reading for display."""

    pid: int
    name: str
    value: float | int | str
    unit: str


class KlineClient:
    """A minimal OBD-II (ISO 9141-2) tester over any :class:`Transport`.

    Talks to a *real* ECU (the confirmed protocol), independent of the virtual
    ECU. Use :class:`~gems_t4.transport.pico.PicoAdapterTransport` for the USB
    Pico on the bench or on-car.
    """

    def __init__(self, transport: Transport) -> None:
        self.transport = transport
        self._supported: set[int] | None = None

    # -- lifecycle -------------------------------------------------------- #
    def connect(self, mode: str = "slow") -> InitResult:
        """Open the transport and 5-baud-init the ECU at address 0x33."""
        self.transport.open()
        return self.transport.init(KLINE_INIT_ADDRESS, mode)

    def close(self) -> None:
        self.transport.close()

    def __enter__(self) -> "KlineClient":
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- core exchange ---------------------------------------------------- #
    def raw_service(self, payload: bytes) -> bytes | None:
        """Send one OBD service request; return the response data (service byte
        + rest) or ``None`` if the ECU stays silent.

        A silent ECU is normal and not an error — e.g. Mode 03 with no stored
        codes. This is also the extension point for proprietary GEMS services
        that share the ``68 6A F1`` envelope.
        """
        try:
            self.transport.send(encode_request(payload))
        except TransportTimeout:
            return None
        return decode_response(self.transport.receive())

    # -- OBD-II services -------------------------------------------------- #
    def supported_pids(self, refresh: bool = False) -> set[int]:
        """Mode 01 PID 00 -> the set of supported PIDs 0x01..0x20 (cached)."""
        if self._supported is not None and not refresh:
            return self._supported
        data = self.raw_service(bytes([0x01, 0x00]))
        if not data or len(data) < 6 or data[0] != 0x41:
            self._supported = set()
        else:
            mask = int.from_bytes(data[2:6], "big")
            self._supported = {p for p in range(1, 33) if mask & (1 << (32 - p))}
        return self._supported

    def read_pid(self, pid: int) -> bytes | None:
        """Mode 01 <pid> -> the raw value bytes (after the echoed pid), or None."""
        data = self.raw_service(bytes([0x01, pid]))
        if not data or len(data) < 2 or data[0] != 0x41 or data[1] != pid:
            return None
        return data[2:]

    def read_live(self) -> list[LiveRow]:
        """Read every catalog PID the ECU supports; return decoded rows."""
        supported = self.supported_pids()
        rows: list[LiveRow] = []
        for spec in PIDS:
            if spec.pid not in supported:
                continue
            raw = self.read_pid(spec.pid)
            if raw is None:
                continue
            try:
                value: float | int | str = spec.decode(raw)
            except Exception:
                value = raw.hex()
            rows.append(LiveRow(spec.pid, spec.name, value, spec.unit))
        return rows

    def read_dtcs(self) -> list[str]:
        """Mode 03 -> stored DTC strings (empty list when there are none)."""
        data = self.raw_service(bytes([0x03]))
        if not data or data[0] != 0x43:
            return []
        return decode_dtcs(data[1:])

    def read_pending_dtcs(self) -> list[str]:
        """Mode 07 -> pending DTC strings (empty when none)."""
        data = self.raw_service(bytes([0x07]))
        if not data or data[0] != 0x47:
            return []
        return decode_dtcs(data[1:])
