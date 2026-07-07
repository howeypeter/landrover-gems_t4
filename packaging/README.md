# Packaging — PyInstaller Windows build (Phase 6)

Builds a standalone Windows executable of `gems_t4` so it runs on a machine
with no Python installed. The default build is a **console** app: every CLI
subcommand works from the exe (`scenarios`, `live`, `dtc`, `actuator`,
`coding`, `immo`, and `gui`). The `gui` subcommand launches the PySide6
window, so PySide6/Qt is bundled.

Two variants are described here:

1. **Console CLI** (built and validated) — `packaging/gems_t4.spec`. One folder,
   `gems_t4.exe` opens a console; `gems_t4.exe gui` still opens the GUI window.
2. **Windowed GUI kiosk** (documented, not built) — a `console=False` variant
   that boots straight into the GUI with no console window.

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

## Build (console CLI)

Run from the **repo root** (not from `packaging/`):

```
.venv\Scripts\python.exe -m PyInstaller packaging/gems_t4.spec --distpath dist --workpath build/pyi --noconfirm
```

- **Output**: `dist/gems_t4/` (a one-dir bundle; `dist/` is gitignored).
- **Entry point**: `packaging/_entry.py` → `gems_t4.app.cli:main`.
- **Mode**: one-dir (`COLLECT`). One-dir is deliberate — it is far more reliable
  for the large PySide6/Qt payload than one-file, which unpacks Qt to a temp
  directory on every launch (slow start, occasional AV false-positives).

The spec collects PySide6 wholesale via `collect_all("PySide6")` plus a few
defensive `hiddenimports` for the `gems_t4.app` packages, and excludes test-only
packages (`pytest`, `pytest_qt`, `tkinter`).

## Run

```
dist\gems_t4\gems_t4.exe --version      # -> gems_t4 0.1.0
dist\gems_t4\gems_t4.exe scenarios      # lists the 4 fault scenarios
dist\gems_t4\gems_t4.exe live --scenario coolant_sensor
dist\gems_t4\gems_t4.exe dtc read --scenario misfire_cyl3
dist\gems_t4\gems_t4.exe gui            # opens the PySide6 window
```

Ship the **entire `dist/gems_t4/` folder** — `gems_t4.exe` depends on the DLLs
and `_internal/` payload beside it. To distribute, zip the folder.

### Validated output (console build)

```
> dist\gems_t4\gems_t4.exe --version
gems_t4 0.1.0

> dist\gems_t4\gems_t4.exe scenarios
Available fault scenarios:
  - healthy
  - coolant_sensor
  - misfire_cyl3
  - lambda_heater
```

## Windowed GUI-only kiosk variant (not built — documentation only)

For a kiosk build that boots straight into the GUI with **no console window**,
create a second spec (e.g. `packaging/gems_t4_gui.spec`) that is identical to
`gems_t4.spec` except:

- **Entry script**: a shim that calls the GUI directly instead of the CLI:

  ```python
  # packaging/_entry_gui.py
  import sys
  from gems_t4.app.gui.app import run
  if __name__ == "__main__":
      sys.exit(run())
  ```

- **`EXE(... console=False ...)`** — no console window; unhandled tracebacks go
  to a dialog rather than stdout.
- **`name="gems_t4_gui"`** on both `EXE(...)` and `COLLECT(...)` so it lands in
  `dist/gems_t4_gui/` and does not collide with the console build.
- (Optional) add an `icon="...ico"` argument to `EXE(...)` for a branded kiosk
  icon.

Build it the same way:

```
.venv\Scripts\python.exe -m PyInstaller packaging/gems_t4_gui.spec --distpath dist --workpath build/pyi --noconfirm
```

Output: `dist/gems_t4_gui/gems_t4_gui.exe` — double-clicking opens the T4 GUI
directly. `gems_t4.app.gui.app:run(scenario="healthy")` is the entry; pass a
different scenario by editing the shim if the kiosk should boot a specific fault.

## Notes / gotchas

- **`.gitignore` ignores `*.spec`.** The repo's `.gitignore` has a broad
  `*.spec` rule (intended for PyInstaller *build output*), which also matches
  the hand-written `packaging/gems_t4.spec` and `packaging/gems_t4_gui.spec`.
  These specs are source, not build output — force-add them so they are tracked:

  ```
  git add -f packaging/gems_t4.spec
  ```

  (Alternatively, add a negation to `.gitignore`: `!packaging/*.spec`.)
- **Build from the repo root**, so `pathex`/`SPECPATH` resolve `gems_t4` on the
  import path. Building from inside `packaging/` will fail to find the package.
- **Clean rebuild**: delete `build/pyi/gems_t4` and `dist/gems_t4` (or just pass
  `--noconfirm`, which overwrites in place).
- **One-file** is possible (`--onefile` / an `EXE` with `exclude_binaries=False`
  and no `COLLECT`) but not recommended here because of the Qt unpack-on-launch
  cost; stick with one-dir.
