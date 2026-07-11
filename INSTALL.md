# Installing and running gems_t4

## Prerequisites

- **Python 3.11+** (developed against 3.14).
- **Windows** is the primary target (the GUI launcher scripts below are
  Windows `.bat`/`.ps1`), but the CLI and test suite are plain cross-platform
  Python and run on macOS/Linux too.

## 1. Create a virtual environment and install

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt     # CLI only
# ...or, for the GUI too:
pip install -e ".[gui]"
```

Use the venv's Python for everything below (activate once, or prefix commands
with `.venv\Scripts\`). PySide6 (the GUI) is intentionally kept out of
`requirements.txt` — it's a large optional dependency — so install it via the
`[gui]` extra if you want the kiosk GUI, not just the CLI.

## 2. Verify it works

```powershell
python -m gems_t4 scenarios
```

This should list the four built-in fault scenarios with no hardware attached
— the tool ships with a full virtual ECU, so nothing else is required to try
it out.

## 3. Run the GUI

```powershell
python -m gems_t4 gui
```

**On Windows, `launch_gui.bat`** (in the project root) is the quick way in —
double-click it, or run it from a shell. It launches the **live venv source**
(`.venv\Scripts\pythonw -m gems_t4 gui`), not a pre-built executable, so it
always reflects whatever is currently checked out — after a `git pull` there
is nothing to rebuild. `create_shortcut.ps1` makes a desktop shortcut that
does the same thing.

The GUI shows its version (`gems_t4 v<version>`) on the boot splash and in
the window title on every launch, so you can always tell which build you're
running.

Add `--instant` (`gems_t4 gui --instant`) to skip the period-authentic
"Communicating with ECU… please wait" delays during development/testing.

## Updating

There is no separate "update" step beyond pulling the latest code — the venv
launcher (`launch_gui.bat`, `python -m gems_t4 gui`) always runs live source.
If you added new dependencies since your last `pip install`, re-run step 1's
`pip install` line.

## Optional: connect to real hardware

The tool talks to a Raspberry Pi **Pico** or **Pico 2** + a K-line
transceiver over USB, or to a remote ECU link over TCP/network. Neither is
required to use the tool — the virtual ECU covers the full feature set for
development, demos, and learning the workflow.

- **USB Pico adapter** — parts list, wiring, and firmware flashing are in
  [`firmware/README.md`](firmware/README.md).
- **Network / remote ECU** — `gems_t4 serve` and the `--connect HOST[:PORT]`
  flag (or the GUI's **Configuration — VCI connection** screen) reach an ECU
  over TCP. See the "Remote / network use" section of [`README.md`](README.md).

## Optional: build a standalone Windows executable

If you want a `.exe` you can hand to someone without a Python install, use
the `[build]` extra and PyInstaller:

```powershell
pip install -e ".[build]"
```

Then follow [`packaging/README.md`](packaging/README.md), which builds one
`dist/gems_t4/` folder containing `gems_t4.exe` (console — the CLI) and
`gems_t4_gui.exe` (windowed, no console — the kiosk GUI).

**Known gotcha:** the bundled exe can go stale — Qt/PyInstaller bytecode
caches persist even after `--clean` rebuilds. If it doesn't reflect your
latest source changes, delete `packaging/build/` and `dist/` before
rebuilding, or just run from the venv instead (see "Run the GUI" above),
which is what `launch_gui.bat` does by default for exactly this reason.

## Development / running the test suite

```powershell
pytest                    # the main suite (GUI tests skip cleanly without PySide6/[gui])
pytest tests_regression   # an independent regression suite — run explicitly
```

Build contracts that pin the wire format, service map, and every module's
public API live in [`docs/INTERFACES.md`](docs/INTERFACES.md) (core) and
[`docs/GUI_INTERFACES.md`](docs/GUI_INTERFACES.md) (GUI screens).
