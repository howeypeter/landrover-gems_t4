# Packaging — PyInstaller Windows build (Phase 6)

Builds standalone Windows executables of `gems_t4` so it runs on a machine
with no Python installed. One build produces **two exes side by side in a
single one-dir bundle**, sharing one copy of the PySide6/Qt payload:

1. **Console CLI** — `gems_t4.exe`. Every CLI subcommand works from the exe
   (`scenarios`, `live`, `dtc`, `actuator`, `coding`, `immo`, and `gui`).
   This is the dev/hacking tool; `gems_t4.exe gui` still opens the GUI window
   (with a console behind it).
2. **Windowed GUI kiosk** — `gems_t4_gui.exe` (`console=False`). Boots straight
   into the PySide6 T4 GUI with **no console window** — the kiosk experience.
   Double-click it, or pass `--scenario` to boot into a specific fault.

Both are built by the one spec, `packaging/gems_t4.spec`, into `dist/gems_t4/`.

## Prerequisites

From the repo root, using the project venv:

```
.venv\Scripts\python.exe -m pip install "pyinstaller>=6.0"
.venv\Scripts\python.exe -m pip install -e ".[gui]"     # ensures PySide6 present
```

Or, equivalently, install the packaging extra added to `pyproject.toml`:

```
.venv\Scripts\python.exe -m pip install -e ".[gui,build]"
```

## Build

Run from the **repo root** (not from `packaging/`):

```
.venv\Scripts\python.exe -m PyInstaller packaging/gems_t4.spec --distpath dist --workpath build/pyi --noconfirm
```

- **Output**: `dist/gems_t4/` (a one-dir bundle; `dist/` is gitignored)
  containing BOTH `gems_t4.exe` and `gems_t4_gui.exe`.
- **Entry points**: `packaging/_entry.py` -> `gems_t4.app.cli:main` (console);
  `packaging/_entry_gui.py` -> `gems_t4.app.gui.app:run` (windowed).
- **Mode**: one-dir (`COLLECT`). One-dir is deliberate — it is far more reliable
  for the large PySide6/Qt payload than one-file, which unpacks Qt to a temp
  directory on every launch (slow start, occasional AV false-positives).
- **Spec shape**: the two entry scripts each get their own `Analysis` (built by
  a shared `make_analysis()` helper so options cannot drift), two `EXE`s
  (`console=True` / `console=False`), and ONE `COLLECT` — so the two exes share
  a single `_internal/` payload instead of shipping Qt twice.

The spec collects PySide6 wholesale via `collect_all("PySide6")` plus a few
defensive `hiddenimports` for the `gems_t4.app` packages, and excludes test-only
packages (`pytest`, `pytest_qt`, `tkinter`).

## Run

Console CLI:

```
dist\gems_t4\gems_t4.exe --version      # -> gems_t4 0.0.4
dist\gems_t4\gems_t4.exe scenarios      # lists the 4 fault scenarios
dist\gems_t4\gems_t4.exe live --scenario coolant_sensor
dist\gems_t4\gems_t4.exe dtc read --scenario misfire_cyl3
dist\gems_t4\gems_t4.exe gui            # opens the PySide6 window (console behind)
```

Windowed GUI kiosk (no console window — double-click or run from a shortcut):

```
dist\gems_t4\gems_t4_gui.exe
dist\gems_t4\gems_t4_gui.exe --scenario coolant_sensor
```

Ship the **entire `dist/gems_t4/` folder** — both exes depend on the DLLs
and `_internal/` payload beside them. To distribute, zip the folder.

### Validated output

```
> dist\gems_t4\gems_t4.exe --version
gems_t4 0.0.4

> dist\gems_t4\gems_t4.exe scenarios
Available fault scenarios:
  - healthy
  - coolant_sensor
  - misfire_cyl3
  - lambda_heater
```

`gems_t4_gui.exe` validated headless (`QT_QPA_PLATFORM=offscreen`): launches,
stays alive with clean stderr (with and without `--scenario coolant_sensor`),
and shows no console window (`console=False`).

## Notes / gotchas

- **`.gitignore` ignores `*.spec`.** The repo's `.gitignore` has a broad
  `*.spec` rule (intended for PyInstaller *build output*), which also matches
  the hand-written `packaging/gems_t4.spec`. The spec is source, not build
  output — force-add it so it is tracked:

  ```
  git add -f packaging/gems_t4.spec
  ```

  (Alternatively, add a negation to `.gitignore`: `!packaging/*.spec`.)
- **Build from the repo root**, so `pathex`/`SPECPATH` resolve `gems_t4` on the
  import path. Building from inside `packaging/` will fail to find the package.
- **Windowed mode swallows tracebacks.** With `console=False` there is no
  stdout/stderr; an unhandled exception at startup shows a small error dialog
  (or nothing). If `gems_t4_gui.exe` dies silently, debug via the console
  build first: `gems_t4.exe gui` exercises the same GUI code with visible
  tracebacks.
- **No extra Qt plugin work was needed for windowed mode** — both exes share
  the same `collect_all("PySide6")` payload (platform plugins included), so
  windowed vs console only changes the bootloader subsystem flag.
- **Clean rebuild**: delete `build/pyi/gems_t4` and `dist/gems_t4` (or just pass
  `--noconfirm`, which overwrites in place).
- **One-file** is possible (`--onefile` / an `EXE` with `exclude_binaries=False`
  and no `COLLECT`) but not recommended here because of the Qt unpack-on-launch
  cost; stick with one-dir.
