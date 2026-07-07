"""Shared pytest fixtures / setup.

Force Qt to the offscreen platform so the GUI tests run headless (no display
needed on CI or in a plain terminal). Must happen before any PySide6 import.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
