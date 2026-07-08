# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the gems_t4 executables.

Builds a single one-dir bundle named ``gems_t4`` containing TWO entry-point
exes that share the same libs/payload:

- ``gems_t4.exe``     — console CLI (via ``packaging/_entry.py``). Every CLI
  subcommand works from the frozen exe, including ``gems_t4.exe gui`` which
  imports and launches the PySide6 GUI.
- ``gems_t4_gui.exe`` — windowed (``console=False``) kiosk variant (via
  ``packaging/_entry_gui.py``). Boots straight into the PySide6 GUI with no
  console window; accepts ``--scenario``.

Build from the repo root::

    .venv\\Scripts\\python.exe -m PyInstaller packaging/gems_t4.spec \\
        --distpath dist --workpath build/pyi --noconfirm

Output lands in ``dist/gems_t4/`` (gitignored). Run it with::

    dist\\gems_t4\\gems_t4.exe --version
    dist\\gems_t4\\gems_t4.exe scenarios
    dist\\gems_t4\\gems_t4_gui.exe

One-dir mode is deliberate: it is far more reliable for the large PySide6
(Qt) payload than one-file, which would unpack Qt to a temp dir on every
launch. Both exes feed one COLLECT so the Qt payload is shipped once.
"""
import os

from PyInstaller.utils.hooks import collect_all

# ``__file__`` isn't defined when a spec is exec'd, so anchor paths on the
# spec's own directory captured by PyInstaller as ``SPECPATH``.
here = os.path.abspath(SPECPATH)          # noqa: F821  (injected by PyInstaller)
repo_root = os.path.dirname(here)
entry = os.path.join(here, "_entry.py")
entry_gui = os.path.join(here, "_entry_gui.py")

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

# Both entry scripts need their own Analysis (an Analysis with two scripts
# would run them back-to-back in ONE exe, not build two). Options are shared
# via this helper so the two analyses cannot drift apart.
def make_analysis(script):
    return Analysis(
        [script],
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


a = make_analysis(entry)          # console CLI
a_gui = make_analysis(entry_gui)  # windowed GUI kiosk

pyz = PYZ(a.pure)
pyz_gui = PYZ(a_gui.pure)

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

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    [],
    exclude_binaries=True,
    name="gems_t4_gui",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # windowed kiosk: no console window behind the GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# One COLLECT with both exes -> a single dist/gems_t4/ folder where the two
# exes sit side by side sharing one copy of the Qt/_internal payload.
# COLLECT de-duplicates the (identical) binaries/datas from both analyses.
coll = COLLECT(
    exe,
    exe_gui,
    a.binaries,
    a.datas,
    a_gui.binaries,
    a_gui.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="gems_t4",
)
