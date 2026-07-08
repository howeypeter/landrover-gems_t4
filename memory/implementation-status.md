---
name: implementation-status
description: Build status of the gems_t4 Python codebase — what exists, how it's structured, how to run and validate it
metadata:
  type: project
---

**Phases 1–6 COMPLETE. 123 passing tests** (74 + 10 skipped without the PySide6
`[gui]` extra; both counts verified empirically). Phase 3 real-hardware on-car
validation still pending HW.

## Phase 6 COMPLETE (2026-07-07) — built by a 5-agent fan-out
- **Gauge widgets:** `app/gui/widgets.py` — QPainter `DialGauge` (270° arc,
  needle, redline, bevel ring), `BarGauge` (sunken track), `LcdReadout`;
  `build_gauge(spec)` dispatches by style. `app/gui/gauge_specs.py` — per-param
  scale/redline/decimals/style; `spec_for` synthesises a dial for unlisted ids.
  Gauges FIXED-size (184×150 dial / 184×66 bar+lcd); live_data screen rebuilds a
  `QGridLayout` (4 cols) and pushes values each timer tick.
- **"The waiting":** `app/gui/wait.py` — "Communicating with ECU - please wait"
  overlay + `KioskWindow.run_with_wait(label, fn, on_done, on_error)`: runs
  backend ops on a background thread, enforces a minimum display time, click
  skips the remaining wait, nav bar disabled in flight. `GEMS_T4_INSTANT=1` (or
  `gui --instant`) = synchronous instant mode; tests/conftest.py sets it so all
  GUI tests are deterministic. Wired into vehicle_id, fault_codes, actuators,
  immobiliser, coding (NOT live_data — its QTimer IS the bandwidth model; NOT
  boot — own timed sequence).
- **Win98 skin:** style.py rebuilt on per-side bevel fragments (white
  top-left/dark bottom-right), 16px beveled scrollbars, combo drop-downs,
  #ffffe1 tooltip, checkbox/radio, dotted focus, segmented marching-blocks
  progress bar. GOTCHA: pure-QSS border-triangle arrows render as black
  rectangles in Qt — style.py rasterises tiny glyph PNGs via QImage at import
  (pre-QApplication-safe) and references them with url(). Screenshot iteration
  must use the native `windows` platform (offscreen has no fonts → tofu).
- **$61 params 24 → 37:** injector PW (0x17), coil charge (0x18), purge duty
  (0x1B), fuel pump (0x1C), run time (0x1D, fed from sim clock in tick()),
  per-cylinder misfires 0x20–0x27 (1-byte, saturate at 255). misfire_cyl3 puts
  the whole count on cyl 3 (`misfire_cyl3 = misfire_total`), others 0.
  coolant_sensor adds injector_pw=3.8 (cold-reading enrichment).
- **Two-exe PyInstaller bundle:** `packaging/gems_t4.spec` builds console
  `gems_t4.exe` (entry `_entry.py`) AND windowed `gems_t4_gui.exe` (entry
  `_entry_gui.py`, console=False) into ONE `dist/gems_t4/` COLLECT. Validated:
  console exe --version/scenarios; GUI exe stays alive offscreen.
- **E2E QA:** `tests/test_gui_e2e.py` — 6 tests through the production
  `build_window` wiring (nav tour incl. back-stack unwind, misfire diagnostic
  session read→clear→re-read, gauge sweep + interval monotonicity, refusal
  propagation to status bar, wait-overlay lifecycle, all-screen paint smoke).
  All derive counts dynamically from PARAMETERS/registry — sibling-safe.
- **Fan-out lesson (again):** 4 parallel agents → 2 stalled mid-stream (API),
  resumed via SendMessage with updated baselines and finished clean.

## What exists
- Python package `gems_t4` at the repo root. Deps via `requirements.txt` (or
  `pip install -e .`, which also adds a `gems_t4` console script). Run with
  `python -m gems_t4 <cmd>`. ~2,500 LOC, **45 passing pytest tests**, no hardware
  needed. Python 3.14 venv at `.venv/`. NOTE: command is `gems_t4` (underscore,
  matching the folder) — the old `gems-t4` hyphen name was removed 2026-07-07.
- Layers: `transport/` (base, virtual, pico, ftdi-stub) · `protocol/` (messages,
  framing, timing, init, security, client) · `gems/` (types, ecu_base, dtc,
  livedata, actuators, ecu_profile, programming, scenarios, virtual_ecu) · `app/`
  (backend facade, cli, render, **gui/**). Plus `firmware/` (HOST_PROTOCOL.md,
  pico_kline.ino, README) and `tests/`.
- **GUI added 2026-07-07 (Phase 4):** PySide6 Win98 kiosk in `app/gui/` — a
  Qt-free `Backend` facade (`app/backend.py`) is the seam; `base.py`
  (KioskWindow + Screen), `style.py` (Win98 QSS), `screens/` (boot, vehicle_id,
  system_menu, fault_codes, live_data, actuators, toolbox), `app.py` entry.
  Launch `gems_t4 gui [--scenario X]` or `python -m gems_t4.app.gui`; needs the
  `[gui]` extra. Contract: `GUI_INTERFACES.md`. Tests headless via
  `QT_QPA_PLATFORM=offscreen` (tests/conftest.py) + pytest-qt. Each GUI test file
  starts with `pytest.importorskip("PySide6")` so a plain requirements.txt install
  gives "N passed, K skipped" not errors.
- **Phase 5 added 2026-07-07 (programming/coding):** `gems/immobiliser.py`
  (Security-Learn = the one genuine GEMS K-line write; virtual-ECU `$31` routines
  + `VirtualEcu(immobilised=True)` reproduces "ENGINE IMMOBILISED" and recovers
  it), `gems/programming.py` (gated coding: backup+verify+confirm; +ASCII/hex
  codecs), `gems/maps.py` (read-only chip-swap lookalike: 27C512/27C1001 EPROM
  facts + 16×16 fuel/ignition tables). Backend methods + CLI (`coding read|write`,
  `immo status|learn`) + GUI screens (programming_menu → coding/immobiliser/maps).
- CLI works: `python -m gems_t4 scenarios | live [--scenario X --ids ..] | dtc
  read|clear | actuator NAME --state on|off | coding read|write --field K --value V
  | immo status|learn [--immobilised] | gui`, all `--fake` by default; `--port
  COMx` → Pico.

## Key facts for the next session
- **Frozen contract is `INTERFACES.md`** at the repo root — wire format, SID map,
  each module's public API, module ownership. Build against it.
- Wire frame: `[0x80][TGT][SRC][LEN][data][CS]`, CS = sum mod 256. Stylized
  KWP2000 (GEMS bytes not public — the virtual ECU defines a coherent dialect).
- Load-bearing seam: `KwpClient(transport)` takes VirtualTransport or
  PicoAdapterTransport. Virtual path is instant (no sleeps) → fully testable.
- Four scenarios coherent across DTC/live/actuator: healthy, coolant_sensor
  (P0118, coolant reads -40), misfire_cyl3 (P0303), lambda_heater (P1185, refuses
  O2-heater test). Fuel-pump actuator refused while engine running.
- Pico is a *timed byte pipe*; host protocol in `firmware/HOST_PROTOCOL.md`
  (0xA5/0x5A framing, crc8=XOR, PING/INIT/SEND_RECV/SET_TIMING). `pico.py` and the
  `.ino` both implement it; unit-tested via a fake serial loopback.

## How to validate
`.venv/Scripts/python.exe -m pytest`  (expect `123 passed` with the `[gui]`/`[dev]`
extra; `74 passed, 10 skipped` on a plain requirements.txt install without PySide6).

## Not yet built (next steps)
- **Phase 3 real hardware:** on-car / bench validation of the Pico path (needs
  the hardware); FTDI transport is still a documented stub.
- Optional Td5/MEMS3 profile for a *real* documented over-the-wire reflash demo
  (the one flashable Rover engine ECU — contrast to GEMS's chip-swap).
- Optional polish: exe icon/version resources, guided fault trees, Pico 2 W
  wireless read-only mode (parked — see CLAUDE.md, do not start unprompted).

Related: [[tech-stack-decision]], [[research-synthesis]],
[[research-python-architecture]], [[workflow-directives]].
