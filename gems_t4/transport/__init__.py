"""Transport layer: the only code aware of I/O and (on real hardware) timing.

A Transport moves *complete* KWP frames (header .. checksum) to and from an ECU.
It does not interpret them — framing lives in :mod:`gems_t4.protocol.framing`.
Implementations: VirtualTransport (in-memory link to the virtual ECU),
PicoAdapterTransport (USB-CDC link to the Pico smart adapter), and a raw
FTDI-cable transport.
"""
