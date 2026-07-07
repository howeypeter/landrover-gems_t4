---
name: implementation-status
description: Build status of the gems_t4 Python codebase — what exists, how it's structured, how to run and validate it
metadata:
  type: project
---

**Phases 1–5 complete; Phase 6 in progress. 99 passing tests** (65 + 8 skipped
without the PySide6 `[gui]` extra). Phase 3 real-hardware on-car validation still
pending HW.

## Phase 6 progress (2026-07-07)
- **Gauge widgets DONE:** `app/gui/widgets.py` — QPainter `DialGauge` (270° arc,
  needle, redline), `BarGauge`, `LcdReadout`; `build_gauge(spec)` dispatches by
  style. `app/gui/gauge_specs.py` — per-param scale/redline/decimals/style
  (`GAUGE_SPECS` keyed by live-data local id; `spec_for` synthesises a dial for
  unlisted ids). Gauges are FIXED-size (184×150 dial / 184×66 bar+lcd) so the grid
  lays out; live_data screen rebuilds a `QGridLayout` (4 cols, top-left aligned)
  and pushes values each timer tick. Visually verified via `w.grab()` PNGs.
- **PyInstaller build DONE:** `packaging/gems_t4.spec` (one-dir console exe,
  `collect_all("PySide6")`), `packaging/_entry.py` shim, `packaging/README.md`.
  Built exe validated (`--version`, `scenarios`). `build` extra in pyproject.
  Build to `dist/gems_t4/` (gitignored). `.gitignore` has `!packaging/*.spec` so
  the hand-written spec is trackable despite the `*.spec` rule.
- **Still to do (Phase 6):** "the waiting" latency overlay, background worker
  thread (only needed for slow real HW), full Win98 skin refinement, windowed
  GUI-only exe variant, more $61 params (24/~35).

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
`.venv/Scripts/python.exe -m pytest`  (expect `93 passed` with the `[gui]`/`[dev]`
extra; `~75 passed, N skipped` on a plain requirements.txt install without PySide6).

## Not yet built (next steps)
- **Phase 3 real hardware:** on-car / bench validation of the Pico path (needs
  the hardware); FTDI transport is still a documented stub.
- **Phase 6 polish:** real gauge widgets (live-data + maps are table-based), the
  "the waiting" latency overlay, a background worker thread for slow real hardware
  (GUI is single-threaded / QTimer-polled — fine for the instant virtual ECU),
  full Win98 skin refinement, PyInstaller Windows build.
- Optional Td5/MEMS3 profile for a *real* documented over-the-wire reflash demo
  (the one flashable Rover engine ECU — contrast to GEMS's chip-swap).
- More of the ~35 live params (24 implemented).

Related: [[tech-stack-decision]], [[research-synthesis]],
[[research-python-architecture]], [[workflow-directives]].
