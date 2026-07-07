"""GUI entry point — builds the QApplication, the Backend, and the kiosk window,
registers every screen, and starts on the boot splash.

Run with ``python -m gems_t4.app.gui`` or ``gems_t4 gui`` (optionally
``--scenario coolant_sensor``).
"""
from __future__ import annotations

import sys

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import KioskWindow
from gems_t4.app.gui.screens.actuators import ActuatorsScreen
from gems_t4.app.gui.screens.boot import BootScreen
from gems_t4.app.gui.screens.coding import CodingScreen
from gems_t4.app.gui.screens.fault_codes import FaultCodesScreen
from gems_t4.app.gui.screens.immobiliser import ImmobiliserScreen
from gems_t4.app.gui.screens.live_data import LiveDataScreen
from gems_t4.app.gui.screens.maps import MapsScreen
from gems_t4.app.gui.screens.programming_menu import ProgrammingMenuScreen
from gems_t4.app.gui.screens.system_menu import SystemMenuScreen
from gems_t4.app.gui.screens.toolbox import ToolboxScreen
from gems_t4.app.gui.screens.vehicle_id import VehicleIdScreen

#: name -> screen class, in registration order. The first is the start screen.
SCREENS = {
    "boot": BootScreen,
    "vehicle_id": VehicleIdScreen,
    "system_menu": SystemMenuScreen,
    "fault_codes": FaultCodesScreen,
    "live_data": LiveDataScreen,
    "actuators": ActuatorsScreen,
    "toolbox": ToolboxScreen,
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


def run(scenario: str = "healthy") -> int:
    """Launch the GUI. Returns the Qt exit code."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    backend = Backend(scenario)
    window = build_window(backend)
    window.show()
    return app.exec()


def main() -> int:  # pragma: no cover - thin wrapper
    return run()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(run())
