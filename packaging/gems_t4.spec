# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the gems_t4 console executable.

Builds a one-dir bundle named ``gems_t4`` whose entry point is the CLI
``main()`` (via the ``packaging/_entry.py`` shim). Every CLI subcommand
works from the frozen exe, including ``gems_t4.exe gui`` which imports and
launches the PySide6 GUI.

Build from the repo root::

    .venv\\Scripts\\python.exe -m PyInstaller packaging/gems_t4.spec \\
        --distpath dist --workpath build/pyi --noconfirm

Output lands in ``dist/gems_t4/`` (gitignored). Run it with::

    dist\\gems_t4\\gems_t4.exe --version
    dist\\gems_t4\\gems_t4.exe scenarios

One-dir mode is deliberate: it is far more reliable for the large PySide6
(Qt) payload than one-file, which would unpack Qt to a temp dir on every
launch. For a windowed, GUI-only kiosk build see packaging/README.md.
"""
import os

from PyInstaller.utils.hooks import collect_all

# ``__file__`` isn't defined when a spec is exec'd, so anchor paths on the
# spec's own directory captured by PyInstaller as ``SPECPATH``.
here = os.path.abspath(SPECPATH)          # noqa: F821  (injected by PyInstaller)
repo_root = os.path.dirname(here)
entry = os.path.join(here, "_entry.py")

# Pull in PySide6 wholesale so ``gems_t4.exe gui`` has the full Qt runtime
# (binaries, data, plugins, and any dynamically-imported submodules).
# PyInstaller ships PySide6 hooks, but collect_all is belt-and-braces.
pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all("PySide6")

# Ensure the gems_t4 submodules that are only reached via string dispatch /
# lazy import are pulled in too. Explicit imports in cli.py already cover most,
# but list the app-layer packages defensively.
hiddenimports = pyside_hiddenimports + [
    "gems_t4",
    "gems_t4.app.cli",
    "gems_t4.app.gui",
    "gems_t4.app.gui.app",
]


a = Analysis(
    [entry],
    pathex=[repo_root],
    binaries=pyside_binaries,
    datas=pyside_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Test frameworks are never needed in the shipped bundle.
        "pytest",
        "pytest_qt",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="gems_t4",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,           # console app: gems_t4.exe scenarios / live / dtc / ...
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="gems_t4",
)
