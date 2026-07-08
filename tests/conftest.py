"""Shared pytest fixtures / setup.

Force Qt to the offscreen platform so the GUI tests run headless (no display
needed on CI or in a plain terminal). Must happen before any PySide6 import.

Also force "the waiting" (the ECU-communication overlay, gems_t4/app/gui/wait.py)
into instant/synchronous mode so every screen operation completes inline and the
GUI tests stay deterministic. Tests of the async path itself unset this via
monkeypatch.
"""
from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("GEMS_T4_INSTANT", "1")
