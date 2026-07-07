"""PyInstaller entry shim for the gems_t4 console executable.

Kept trivial on purpose: PyInstaller freezes *this* module as the program
entry point, and it simply hands off to the real CLI ``main()``. Building
from a dedicated shim (rather than pointing the spec at the package's
``cli.py`` directly) avoids the ``-m``/``__main__`` ambiguity and keeps the
frozen entry point stable if the CLI internals move.
"""
from __future__ import annotations

import sys

from gems_t4.app.cli import main

if __name__ == "__main__":
    sys.exit(main())
