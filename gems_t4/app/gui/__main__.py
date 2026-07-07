"""Enable ``python -m gems_t4.app.gui``."""
from __future__ import annotations

import sys

from gems_t4.app.gui.app import run

if __name__ == "__main__":
    sys.exit(run())
