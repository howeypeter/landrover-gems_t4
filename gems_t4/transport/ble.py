"""Bluetooth Low Energy transport to the Pico BLE K-line adapter.

Talks the same host protocol as :mod:`gems_t4.transport.pico` (the ``0xA5/0x5A``
frames), but carries it over a **BLE Nordic UART Service (NUS)** instead of a
USB-CDC / Bluetooth-Classic serial port. The Pico firmware is
``firmware/pico_kline_ble/pico_kline_ble.ino``.

Why BLE over Classic SPP: BLE GATT needs **no bonding / no Windows pairing** and
creates **no COM port** — ``bleak`` just connects to the service by name. That
sidesteps the flaky Windows SPP outgoing-COM-port lifecycle entirely.

NUS characteristics (must match the firmware):
    service 6E400001-B5A3-F393-E0A9-E50E24DCCA9E
    RX      6E400002-...   host -> Pico   (we WRITE host frames here)
    TX      6E400003-...   Pico -> host   (we SUBSCRIBE for reply notifications)

Design: ``bleak`` is async, so a private asyncio loop runs on a background
thread; the synchronous ``Transport`` methods drive it with
``run_coroutine_threadsafe``. TX notifications are reassembled into a byte stream
and parsed with the shared :func:`gems_t4.transport.pico.decode_pico`.

⚠️ Reassembly assumes one reply frame per request (the host protocol is strict
request/response), which is why we clear the RX buffer before each exchange.

``is_wireless`` defaults to **False** (writes allowed), matching the trusted
point-to-point Bluetooth link rather than the read-only TCP gate. Set it True if
you want the wireless write-refusal policy to apply over BLE too.
"""
from __future__ import annotations

import asyncio
import threading
from typing import Any

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
    _MODE_CODE,
    decode_pico,
    encode_host,
)

NUS_SERVICE = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # host -> Pico (write)
NUS_TX = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # Pico -> host (notify)

DEFAULT_NAME = "gems-pico"


class BleTransport(Transport):
    """Talk to the Pico BLE K-line adapter over a Nordic UART Service."""

    is_wireless = False  # trusted point-to-point link; writes allowed (like BT SPP)

    def __init__(
        self,
        name_or_address: str = DEFAULT_NAME,
        *,
        timeout: float = 6.0,        # must exceed the Pico's ~3.3 s slow-init
        scan_timeout: float = 12.0,
        write_response: bool = True,  # firmware RX char is Write (with response)
    ) -> None:
        self._target = name_or_address
        self._timeout = timeout
        self._scan_timeout = scan_timeout
        self._write_response = write_response

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._client: Any | None = None
        self._open = False

        # RX reassembly (bytes arrive on the loop thread; consumed on the caller's)
        self._cond = threading.Condition()
        self._rx = bytearray()

    # -- background asyncio loop ------------------------------------------- #
    def _start_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="ble-transport", daemon=True
        )
        self._thread.start()

    def _run(self, coro, timeout: float | None = None):
        assert self._loop is not None
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout)

    def _stop_loop(self) -> None:
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        if self._loop is not None:
            self._loop.close()
        self._loop = None
        self._thread = None

    # -- notification handler (runs on the loop thread) -------------------- #
    def _on_notify(self, _sender: Any, data: bytearray) -> None:
        with self._cond:
            self._rx.extend(bytes(data))
            self._cond.notify_all()

    # -- lifecycle --------------------------------------------------------- #
    def open(self) -> None:
        try:
            from bleak import BleakClient, BleakScanner  # type: ignore
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise TransportError(
                "bleak is required for BleTransport - install with "
                "'pip install bleak' (or the [ble] extra)"
            ) from exc

        self._start_loop()

        async def _connect() -> Any:
            target = self._target
            device = None
            # Address form "AA:BB:.." on Windows, or a name to scan for.
            if ":" in target and len(target.split(":")) == 6:
                device = await BleakScanner.find_device_by_address(
                    target, timeout=self._scan_timeout
                )
            else:
                device = await BleakScanner.find_device_by_name(
                    target, timeout=self._scan_timeout
                )
            if device is None:
                raise TransportError(
                    f"BLE device {target!r} not found (is the Pico powered and "
                    f"advertising as '{DEFAULT_NAME}', and in range?)"
                )
            client = BleakClient(device)
            await client.connect()
            await client.start_notify(NUS_TX, self._on_notify)
            return client

        try:
            self._client = self._run(_connect(), timeout=self._scan_timeout + 10)
        except TransportError:
            self._stop_loop()
            raise
        except Exception as exc:  # bleak errors -> TransportError
            self._stop_loop()
            raise TransportError(f"BLE connect failed: {exc}") from exc
        self._open = True

    def close(self) -> None:
        if self._client is not None:
            try:
                self._run(self._client.disconnect(), timeout=5.0)
            except Exception:  # pragma: no cover - best-effort
                pass
            self._client = None
        self._stop_loop()
        self._open = False

    def is_open(self) -> bool:
        return self._open

    # -- host-protocol exchange ------------------------------------------- #
    def _transceive(self, cmd: int, payload: bytes = b"") -> tuple[int, bytes]:
        if not self._open or self._client is None:
            raise TransportClosed("transport is not open")

        with self._cond:
            self._rx.clear()

        self._run(
            self._client.write_gatt_char(
                NUS_RX, encode_host(cmd, payload), response=self._write_response
            ),
            timeout=self._timeout,
        )
        return self._read_frame(self._timeout)

    def _read_frame(self, timeout: float) -> tuple[int, bytes]:
        """Wait for one complete 0x5A frame from the notification stream."""
        deadline = None
        with self._cond:
            import time

            deadline = time.monotonic() + timeout
            while True:
                self._resync_locked()
                frame = self._extract_locked()
                if frame is not None:
                    return decode_pico(frame)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TransportTimeout("no complete BLE reply frame in time")
                self._cond.wait(remaining)

    def _resync_locked(self) -> None:
        # Drop any leading bytes before the PICO_START marker.
        while self._rx and self._rx[0] != PICO_START:
            del self._rx[0]

    def _extract_locked(self) -> bytes | None:
        if len(self._rx) < 3:
            return None
        length = self._rx[2]
        total = 3 + length + 1
        if len(self._rx) < total:
            return None
        frame = bytes(self._rx[:total])
        del self._rx[:total]
        return frame

    # -- Transport API ----------------------------------------------------- #
    def ping(self) -> bytes:
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
        pending = getattr(self, "_pending", None)
        if pending is None:
            raise TransportTimeout("no buffered response")
        self._pending = None
        return pending
