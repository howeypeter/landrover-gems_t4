"""Allow running the CLI as a module: ``python -m gems_t4 <command>``.

Equivalent to the installed ``gems_t4`` console script.
"""
from __future__ import annotations

import sys

from gems_t4.app.cli import main

if __name__ == "__main__":
    sys.exit(main())
