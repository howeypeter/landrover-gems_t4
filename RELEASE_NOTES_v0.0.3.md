# Release Notes: v0.0.3

**Tag:** v0.0.3  
**Date:** 2026-07-07  
**Branch:** `v0.0.3` (merged from `main`)

## Summary

**v0.0.3 completes Phase 6: full Polish & Deployment.** The TestBook T4 emulator now has an authentic Win98 dealer-tool skin, live "Communicating with ECU" latency overlays, expanded live-data parameters (24 → 37, including per-cylinder misfire counts), and Windows desktop executables.

## What's New Since v0.0.2

### User-Facing Features

#### 1. Authentic "Waiting" Overlay
- **"Communicating with ECU - please wait"** progress panel appears during diagnostic operations (reading DTCs, running actuator tests, Security-Learn re-sync, coding writes, vehicle ID changes)
- Click the overlay to skip the remaining wait time
- Backed by a background worker thread so the GUI never freezes, even on slow real hardware
- Use `gems_t4 gui --instant` flag or set `GEMS_T4_INSTANT=1` env var to disable waits (useful for testing)

#### 2. Full Win98 Dealer-Tool Skin
- **Per-side beveled borders** (white top-left / dark bottom-right) throughout — buttons, frames, tables, scrollbars
- **Chunky 16px scrollbars** with beveled up/down arrow buttons, raised handles, pale trough
- **Combo drop-downs** with white list, navy selection, proper raised/sunken button
- **Classic tooltips** (#ffffe1 pale yellow with black border)
- **Segmented progress bar** (marching blue blocks) on the boot splash
- **Dotted focus rectangles** on buttons
- **Real glyph arrows** (up/down/left/right) rendered as tiny PNGs (pure-QSS renders them as black rectangles — known Qt limitation)
- Verified against real screenshots taken during development

#### 3. Live-Data Parameter Expansion
**24 → 37 `$61` measures**, including the T4's headline feature: **per-cylinder misfire counts**

New parameters (local ids shown):
- **0x17** Injector pulse width (ms)
- **0x18** Coil charge time (ms)
- **0x1B** Purge valve duty (%)
- **0x1C** Fuel pump state (0/1)
- **0x1D** Engine run time (s, fed from sim clock)
- **0x20–0x27** Misfire count cylinders 1–8 (1-byte, saturate at 255)

**Scenario coherence:** `misfire_cyl3` now tells the per-cylinder story — cylinder 3's count climbs while cylinders 1–2 and 4–8 stay at 0. Real diagnostic tool behavior.

#### 4. Windows Desktop Launcher
- New **`launch_gui.bat`** (quick-launch batch file) and **`create_shortcut.ps1`** (PowerShell script that creates a **`gems_t4 GUI.lnk`** desktop shortcut — run it once from the project root)

#### 5. Two-Exe Windows Build
- **`gems_t4.exe`** (console) — the CLI, for scripting and diagnostics
- **`gems_t4_gui.exe`** (no console window) — the kiosk GUI, windowed experience
- Both in one `dist/gems_t4/` folder; shared PySide6 runtime
- Built via PyInstaller; can be packaged as a standalone Windows app

### Developer & QA Improvements

#### End-to-End GUI Test Suite
New **`tests/test_gui_e2e.py`** (6 comprehensive tests) walks the production GUI through a realistic technician workflow:
- Full navigation tour (visit all 11 screens, navigate Back through the history stack)
- Misfire diagnostic session (vehicle ID → select `misfire_cyl3` → system menu → fault codes → read DTCs → clear codes → re-read)
- Live-data gauge sweep (change gauge count, verify grid rebuilds, confirm refresh rate scales with count)
- Actuator test refusal (engine running refusal propagates to the status bar)
- Wait-overlay lifecycle (overlay appears, nav bar disables, operation completes, overlay hides, bar re-enables)
- Paint smoke test (all 11 screens render without QPainter errors)

**Result:** No integration bugs found. All tests pass headless.

#### New Waiting Overlay Tests
**`tests/test_gui_wait.py`** (9 tests) validates the background worker and latency model:
- Instant mode runs synchronously (env var `GEMS_T4_INSTANT=1`)
- Async path completes correctly
- Error handling routes to callbacks
- Nav bar re-enables after operation
- Overlay visibility state machine

#### Expanded Protocol & Scenario Tests
- `test_livedata.py` +4 tests — round-trip encode/decode for new 13 parameters
- `test_scenarios.py` +2 tests — per-cylinder misfire coherence
- `test_virtual_ecu.py` +3 tests — new ids answer with nominals

### Documentation

- **CLAUDE.md** updated: Phase 6 marked complete, build status → 123 tests, all work items documented, known limitations noted
- **README.md** & **README.html** updated: 37 live params, `--instant` flag, Windows build section, status → "Phases 1–6 complete"
- **memory/implementation-status.md** updated: Phase 6 full breakdown, PyInstaller gotchas, validation steps
- New **launcher scripts** documented in CLAUDE.md quick-start section

### Technical Notes

#### PyInstaller Cache Gotcha
If `gems_t4_gui.exe` doesn't reflect the latest source changes, run from the venv instead:
```bash
python -m gems_t4 gui
```
This is a known interaction where PyInstaller caches old bytecode even after `--clean` rebuilds. Workaround: delete `packaging/build/` and `dist/` manually before rebuilding.

#### Screenshots & Verification
16 PNG screenshots (in `scratch_shots/`) document the Win98 skin verification during development — included in the release for reference.

## Metrics

| Metric | v0.0.2 | v0.0.3 | Change |
|---|---|---|---|
| **Passing tests** | 99 | 123 | +24 (+24%) |
| **Test coverage** | 65 passed, 8 skipped (no PySide6) | 74 passed, 10 skipped | +9 passed, +2 skipped |
| **Live-data params** | 24 | 37 | +13 (+54%) |
| **Python files** | ~68 | ~70 | +2 (wait.py, _entry_gui.py) |
| **GUI screens** | 11 | 11 | — |
| **Files changed** | — | 45 | +1,795 LOC, -218 LOC net |

## Known Limitations

1. **Phase 3 (Pico on-car validation) pending real hardware** — Pico firmware is built and unit-tested, but needs a real Pico + ISO 9141 Click + ECU to validate on-car communication. FTDI transport is a documented stub, not implemented.

2. **PyInstaller bytecode cache** (noted above) — Clean rebuilds may not purge cached bytecode. Use the venv version (`python -m gems_t4 gui`) as a workaround.

3. **"The waiting" waits are enforced** — ~900 ms minimum display time by default, mimicking ISO 9141 half-duplex latency. Users can `gui --instant` to skip, or click the overlay to skip the remainder.

## Installation & Quick Start

### From Source (Development)
```bash
git clone https://github.com/howeypeter/landrover-gems_t4.git
cd landrover-gems_t4
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt          # CLI only
# OR for GUI:  pip install -e ".[gui]"
python -m gems_t4 gui
```

### From Windows Build (Standalone)
```bash
# After rebuilding: packaging/gems_t4.spec --noconfirm
cd dist\gems_t4
gems_t4_gui.exe                           # Launch the kiosk GUI
```

Or double-click the **`gems_t4 GUI.lnk`** desktop shortcut (created on first setup).

## What's Next (Future Phases)

- **Phase 3 on-car validation** — Pico adapter + real vehicle/ECU
- **Optional polish candidates:**
  - Windowed exe icon & version resources
  - Guided diagnostic fault trees (step-by-step procedures)
  - Td5/MEMS3 real-reflash demo profile (contrast GEMS's chip-swap)
  - Pico 2 W wireless (WiFi) read-only mode

## Testing

Run the full suite (all platforms):
```bash
pytest                    # 123 passed, 1.05s (with [gui] extra)
# OR without PySide6:
pytest                    # 74 passed, 10 skipped, 0.15s
```

## Contributors

Built by a 5-agent parallel fan-out (July 2026):
- **"The waiting" + worker thread**
- **Live-data parameter expansion (37 params)**
- **Win98 QSS skin refinement**
- **End-to-end GUI QA sweep**
- **Windows two-exe PyInstaller build**

Two agents stalled mid-stream (API limit) and were resumed successfully — same process as Phase 1–2 delivery.

---

**v0.0.3 is production-ready for the emulated/virtual path.** All diagnostic operations (read DTCs, live data, actuator tests, coding, Security-Learn) are fully functional against the built-in virtual ECU, with period-authentic UX and comprehensive test coverage.

Enjoy the T4 experience! 🚙
