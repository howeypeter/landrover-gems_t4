"""Raw FTDI KKL-cable transport (quick-start / read path) — stub.

Unlike the Pico adapter, a bare FTDI KKL cable makes the *host* responsible for
K-line timing: 5-baud slow init (bit-banged), the 10.4 kbaud byte stream, the
half-duplex self-echo, and the FTDI latency-timer=1ms fix. That is real work and
lower priority than the Pico path (which is the canonical transport and the only
one safe for writes), so this is intentionally a documented stub.

Implementation notes for when this is fleshed out:

* Open the port with pyserial at 10400 8N1; on the underlying FTDI device set the
  latency timer to 1 ms (``pyftdi`` or the OS driver) or inter-byte timing smears.
* For 5-baud init, bit-bang the address at 200 ms/bit (pyftdi bit-bang mode),
  then switch to 10400 and read the 0x55 sync byte + keybytes.
* Every transmitted byte is echoed back on the single wire — read and discard the
  echo before the ECU's reply.
"""
from __future__ import annotations

from gems_t4.transport.base import InitResult, Transport


class FtdiKlineTransport(Transport):
    """Placeholder for a bare FTDI KKL-cable K-line transport.

    Prefer :class:`~gems_t4.transport.pico.PicoAdapterTransport`, which offloads
    timing to firmware and is the only transport intended for write operations.
    """

    def __init__(self, port: str, *, baud: int = 10400) -> None:
        self._port = port
        self._baud = baud
        self._open = False

    def open(self) -> None:
        raise NotImplementedError(
            "FtdiKlineTransport is not implemented yet; use PicoAdapterTransport"
        )

    def close(self) -> None:
        self._open = False

    def is_open(self) -> bool:
        return self._open

    def init(self, address: int, mode: str = "slow") -> InitResult:
        raise NotImplementedError("FtdiKlineTransport.init not implemented")

    def send(self, frame: bytes) -> None:
        raise NotImplementedError("FtdiKlineTransport.send not implemented")

    def receive(self, timeout: float | None = None) -> bytes:
        raise NotImplementedError("FtdiKlineTransport.receive not implemented")
