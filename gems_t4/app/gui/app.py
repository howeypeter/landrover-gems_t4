"""GUI entry point — builds the QApplication, the Backend, and the kiosk window,
registers every screen, and starts on the boot splash.

Run with ``python -m gems_t4.app.gui`` or ``gems_t4 gui`` (optionally
``--scenario coolant_sensor``).
"""
from __future__ import annotations

import sys

from gems_t4.app import config as _config
from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import KioskWindow
from gems_t4.app.gui.screens.actuators import ActuatorsScreen
from gems_t4.app.gui.screens.boot import BootScreen
from gems_t4.app.gui.screens.coding import CodingScreen
from gems_t4.app.gui.screens.connection import ConnectionScreen
from gems_t4.app.gui.screens.fault_codes import FaultCodesScreen
from gems_t4.app.gui.screens.immobiliser import ImmobiliserScreen
from gems_t4.app.gui.screens.live_data import LiveDataScreen
from gems_t4.app.gui.screens.maps import MapsScreen
from gems_t4.app.gui.screens.programming_menu import ProgrammingMenuScreen
from gems_t4.app.gui.screens.system_menu import SystemMenuScreen
from gems_t4.app.gui.screens.toolbox import ToolboxScreen
from gems_t4.app.gui.screens.vehicle_id import VehicleIdScreen
from gems_t4.transport.tcp import parse_endpoint

#: name -> screen class, in registration order. The first is the start screen.
SCREENS = {
    "boot": BootScreen,
    "vehicle_id": VehicleIdScreen,
    "system_menu": SystemMenuScreen,
    "fault_codes": FaultCodesScreen,
    "live_data": LiveDataScreen,
    "actuators": ActuatorsScreen,
    "toolbox": ToolboxScreen,
    "connection": ConnectionScreen,
    "programming_menu": ProgrammingMenuScreen,
    "coding": CodingScreen,
    "immobiliser": ImmobiliserScreen,
    "maps": MapsScreen,
}


def build_window(backend: Backend) -> KioskWindow:
    """Construct the kiosk window with all screens registered and boot shown.

    Split out from :func:`run` so tests can build the window (headless) without
    entering the Qt event loop.
    """
    window = KioskWindow(backend)
    for name, cls in SCREENS.items():
        window.register(name, cls(backend))
    window.go("boot")
    return window


def apply_startup_connection(
    backend: Backend,
    *,
    port: str | None = None,
    connect: str | None = None,
    allow_writes: bool = False,
) -> None:
    """Configure the backend's connection for launch.

    Precedence: explicit ``--port``/``--connect`` flags, then the saved
    configuration (written by the connection screen), then the built-in
    virtual ECU. Explicit flags raise on bad values (the user just typed
    them); a bad *saved* config must never stop the GUI from starting — it
    falls back to the virtual ECU and the user can fix it on the connection
    screen.
    """
    if port:
        backend.set_connection("usb", com_port=port)
        return
    if connect:
        host, tcp_port = parse_endpoint(connect)
        backend.set_connection(
            "network", host=host, tcp_port=tcp_port, allow_writes=allow_writes
        )
        return
    cfg = _config.load_config()
    try:
        if cfg.kind == "usb":
            backend.set_connection("usb", com_port=cfg.com_port)
        elif cfg.kind == "network":
            backend.set_connection(
                "network",
                host=cfg.host,
                tcp_port=cfg.tcp_port,
                allow_writes=cfg.allow_writes,
            )
    except (ValueError, TypeError):
        backend.set_connection("virtual")


def run(
    scenario: str = "healthy",
    *,
    port: str | None = None,
    connect: str | None = None,
    allow_writes: bool = False,
) -> int:
    """Launch the GUI. Returns the Qt exit code."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    backend = Backend(scenario)
    apply_startup_connection(
        backend, port=port, connect=connect, allow_writes=allow_writes
    )
    window = build_window(backend)
    window.show()
    return app.exec()


def main() -> int:  # pragma: no cover - thin wrapper
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
