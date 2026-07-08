# Release Notes: v0.0.2

**Branch:** v0.0.2  
**Date:** 2026-07-07  
**Status:** Phases 1, 2, 4, 5 complete + Phase 6 in progress (gauge widgets + PyInstaller)

## Summary

**v0.0.2 adds visual polish and deployment readiness.** The GUI moves from table-based displays to custom-painted analog gauges (dials, bars, LCD readouts), and a PyInstaller Windows build bundles everything into standalone executables. Phase 6 work is half-done; the remaining polish (Win98 skin, latency overlays, expanded params) comes in v0.0.3.

## What's New Since v0.0.1

### Real Gauge Widgets ✨
The live-data screen evolves from a plain table to a grid of period-authentic analog instruments:

#### Gauge Types
- **DialGauge** — 270° swept dial with needle, redline zone, label, and value display
  - Examples: RPM (0–7000, redline 6000), coolant temp (-40–120°C), battery voltage (8–16V)
- **BarGauge** — horizontal fill bar (0–100% style)
  - Examples: throttle angle, calculated load, gearbox retard, purge valve
- **LcdReadout** — amber on dark LCD panel (like a classic message centre)
  - Examples: loop status, misfire count, A/C request, ignition switch, immobiliser state

#### Grid Layout
- Fixed-size gauges (184×150 dials, 184×66 bars/LCDs) for predictable layout
- 4 columns per row on the 800×600 kiosk
- Scrollable grid (QScrollArea) for all 24 parameters

#### Gauge Specifications
New `GaugeSpec` dataclass in `app/gui/gauge_specs.py`:
- Per-parameter scale (vmin/vmax), redline threshold, unit, decimal places, widget style
- 24 explicit specs + a fallback for unknown ids
- `build_gauge(spec)` dispatches to the right widget type

#### Bandwidth Model (Authentic Trade-Off)
- Gauge-count selector (1, 4, 8, 16, or all 24 gauges)
- Refresh rate scales with count: ~20 Hz for 1 gauge → ~0.5 Hz for all 24
- Status bar shows current rate: "4 gauge(s) - refresh 5.0/s (K-line bandwidth)"
- Mimics the real T4's performance trade-off

### PyInstaller Windows Build 🪟
- **Spec:** `packaging/gems_t4.spec` (one-dir layout, PySide6 bundled)
- **Entry script:** `packaging/_entry.py` (shim to call the package's CLI)
- **Build process:** `pip install -e ".[build]"` then `cd packaging && python -m PyInstaller gems_t4.spec --noconfirm`
- **Output:** `dist/gems_t4/gems_t4.exe` (console exe for CLI)
- **Status:** Validated (`--version`, `scenarios` commands work)
- **Not yet:** No windowed variant, no icon/version resources

### Test Expansion
- **GUI tests:** Added 4 pytest-qt test files (8 new tests) for the gauge system
  - `test_gui_gauges.py` — gauge value clamping, fraction calculation, paint smoke
  - Headless-validated via `QT_QPA_PLATFORM=offscreen`
- **Total:** 99 passing tests (up from ~45 in v0.0.1)
- **Coverage:** Full protocol depth + new GUI layer

### Documentation
- **CLAUDE.md** updated: Phase 6 marked "in progress", gauge widgets documented, PyInstaller build noted
- **README.md** & **README.html** updated: ~24 live params (via gauge grid), PyInstaller exe mentioned
- **GUI_INTERFACES.md** updated: screen contracts, gauge specs, layout details

## Metrics

| Metric | v0.0.1 | v0.0.2 | Change |
|---|---|---|---|
| **Passing tests** | 45 | 99 | +54 (+120%) |
| **GUI test files** | 4 | 8 | +4 |
| **Live-data display** | Table | Analog gauges | Aesthetic + authentic |
| **Python files** | ~68 | ~68 | — |
| **PyInstaller exe** | ❌ | ✅ | New |
| **Lines of code (GUI)** | ~2,000 | ~2,500 | +500 (widgets + specs) |

## What's Still In Progress (Phase 6)

- ❌ **Full Win98 skin** — buttons still have default Qt styling; bevels, scrollbars, tooltips not yet themed
- ❌ **"Waiting" overlay** — no latency display during ECU operations yet
- ❌ **Background worker thread** — GUI operations still run on the main thread (fine for the instant virtual ECU, risky for real slow hardware)
- ❌ **37 live parameters** — still at 24 (per-cylinder misfires and other new params coming)
- ❌ **Windowed exe** — only console `gems_t4.exe` so far; `gems_t4_gui.exe` (no-console GUI) coming

These gaps are the focus of the v0.0.3 release.

## What Hasn't Changed

- ✅ Virtual ECU, protocol, CLI — all identical to v0.0.1
- ✅ 4 fault scenarios — all still coherent
- ✅ Security-Learn, coding, maps — all unchanged
- ✅ 11 GUI screens — same wiring, just with gauge grids in live-data

## Installation

```bash
git clone https://github.com/howeypeter/landrover-gems_t4.git
cd landrover-gems_t4
git checkout v0.0.2
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows
pip install -r requirements.txt     # CLI + gauge deps
# OR for GUI:  pip install -e ".[gui]"
python -m gems_t4 gui
```

### Windows Standalone (if built)
```bash
# After: cd packaging && python -m PyInstaller gems_t4.spec --noconfirm
dist\gems_t4\gems_t4.exe --version
dist\gems_t4\gems_t4.exe scenarios
```

## Use Cases for v0.0.2

✅ **Visual demo** — Show off the T4's gauge-rich interface  
✅ **Research** — Explore how gauges should scale with parameter count (bandwidth trade-off)  
✅ **Windows packaging validation** — Test PyInstaller bundling before final polish  
✅ **GUI testing** — Headless validation of paint code without X11/display server  

## Known Limitations

- Gauge widgets are unstyled (no bevels, default Qt appearance)
- PyInstaller exe has old bytecode caching issues (minor, doesn't block usage)
- No authentic K-line latency overlays yet
- Still only 24 live params (37 coming in v0.0.3)
- No windowed GUI exe yet (console exe only)

## Next Steps

**v0.0.3 completes Phase 6:** Full Win98 skin, latency overlays, 37 params, per-cylinder misfires, windowed GUI exe, and comprehensive E2E tests. See [RELEASE_NOTES.md](RELEASE_NOTES.md) for v0.0.3 details.

---

**v0.0.2 is the visual foundation release.** The gauge widgets establish the authentic T4 look; the PyInstaller build proves Windows packaging works. Phase 6 polish lands in v0.0.3, completing the production-ready kiosk experience. 🎨

Use v0.0.2 to see the direction; upgrade to v0.0.3 when you want the full polish.
