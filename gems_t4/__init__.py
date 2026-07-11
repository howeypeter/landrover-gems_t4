"""gems_t4 — a T4-style diagnostic and (emulated) programming tool for the
Lucas/SAGEM GEMS V8 engine ECU fitted to the P38 Range Rover (4.0/4.6) and
Discovery 1 V8i, 1995–early 1999.

Layering (each layer depends only downward):

    app/        presentation — Rich CLI now, PySide6 Win98 GUI later
    gems/       GEMS meaning — DTCs, $61 live data, actuators, virtual ECU, scenarios
    protocol/   KWP2000/ISO-14230 framing, init, services, security, the KwpClient
    transport/  the only I/O layer — virtual ECU link, Pico adapter (USB), FTDI cable

The load-bearing seam is ``KwpClient(transport)``: it takes a real serial
transport OR a VirtualTransport, so the whole stack runs and is tested off-car.
"""

__version__ = "0.0.5"
