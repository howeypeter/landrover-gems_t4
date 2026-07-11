"""The app version must be visible on every launch (window title + boot splash).

Guards the user-facing requirement that launching the GUI always shows which
version is running (tracks the branch/release, e.g. v0.0.5).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QLabel

from gems_t4 import __version__
from gems_t4.app.backend import Backend
from gems_t4.app.gui.app import build_window


def test_version_in_window_title(qtbot):
    win = build_window(Backend("healthy"))
    qtbot.addWidget(win)
    assert f"v{__version__}" in win.windowTitle()


def test_version_on_boot_splash(qtbot):
    win = build_window(Backend("healthy"))
    qtbot.addWidget(win)
    boot = win._screens["boot"]
    boot.on_enter()
    texts = [lbl.text() for lbl in boot.findChildren(QLabel)]
    assert any(f"v{__version__}" in t for t in texts), texts
