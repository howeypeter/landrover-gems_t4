"""PyInstaller entry shim for the windowed gems_t4_gui executable.

Kept trivial on purpose: PyInstaller freezes *this* module as the program
entry point, and it simply hands off to the real GUI ``run()`` (the same
function ``gems_t4 gui`` dispatches to). Building from a dedicated shim
(rather than pointing the spec at ``gems_t4/app/gui/app.py`` directly)
avoids the ``-m``/``__main__`` ambiguity and keeps the frozen entry point
stable if the GUI internals move.

Accepts the same ``--scenario`` flag as ``gems_t4 gui`` so a kiosk shortcut
can boot straight into a specific fault scenario::

    gems_t4_gui.exe --scenario coolant_sensor
"""
from __future__ import annotations

import argparse
import sys

from gems_t4.app.gui.app import run
from gems_t4.gems.scenarios import SCENARIOS

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="gems_t4_gui")
    parser.add_argument("--scenario", default="healthy",
                        choices=sorted(SCENARIOS), help="initial fault scenario")
    args = parser.parse_args()
    sys.exit(run(scenario=args.scenario))
