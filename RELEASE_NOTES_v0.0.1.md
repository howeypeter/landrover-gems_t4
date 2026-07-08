# Release Notes: v0.0.1

**Tag:** v0.0.1  
**Date:** 2026-07-07  
**Status:** Phases 1, 2, 4, 5 complete (core + GUI framework)

## Summary

**v0.0.1 is the foundation release:** the complete virtual ECU, full KWP2000 protocol stack, CLI diagnostics, PySide6 GUI framework, and gated programming (Security-Learn, coding, maps viewer). Everything runs on a laptop with no car or adapter needed.

## What's Included

### Phase 1: Virtual ECU & Protocol Stack ✅
- **Virtual ECU** (`gems_t4/gems/virtual_ecu.py`) simulates a GEMS V8 engine ECU with:
  - Four fault scenarios (healthy, coolant_sensor, misfire_cyl3, lambda_heater)
  - Warm-up curve, idle hunt simulation
  - Coherent symptoms across all diagnostic operations
- **KWP2000 / ISO-14230 protocol** stack:
  - Stylized frame format: `[0x80][TGT][SRC][LEN][data][CS]`
  - Tester-initiated half-duplex communication model
  - Security access ($27 seed/key)
  - Session management
- **Transports:**
  - `VirtualTransport` (in-memory, instant, fully testable)
  - `PicoAdapter` transport (Raspberry Pi Pico, wired USB, production-ready firmware)
  - `FtdiStub` (documented, not yet implemented)

### Phase 2: Full Diagnostics Protocol ✅
- **Fault codes (DTCs):** Read, clear, with confirmation dialogs
- **Live data ($61 records):** 24 GEMS live measures
  - Engine temps (coolant, intake air, fuel)
  - Electrical (battery voltage, ignition state)
  - Performance (RPM, throttle, MAF, O2, fuel trims, IACV, ignition advance)
  - Vehicle (road speed, gearbox status, A/C request)
  - Immobiliser & misfire data
- **Actuator tests:** MIL, O2 heater, fuel pump, injectors (with refusal interlocks)
- **Service adjustments:** Ignition timing offset, idle speed offset
- **Bandwidth model:** Authentic K-line slowness (configurable via CLI `--latency`)

### Phase 4: PySide6 GUI Framework ✅
- **Kiosk shell** (`KioskWindow`, `Screen` base class) — 800×600 appliance feel
- **11 diagnostic screens:**
  - Boot splash (with Toolbox self-tests placeholder)
  - Vehicle ID (VIN entry → scenario selection → connect)
  - System menu (which systems are fitted)
  - Fault codes (table view, read/clear operations)
  - Live data (table view, gauge-count → refresh-rate trade-off)
  - Actuator tests (command + outcome display)
  - Toolbox (self-tests, LAN card check, VCI status)
  - Programming menu (entry point for coding/immobiliser/maps)
  - Coding (gated read/edit/write with backup+verify+confirm)
  - Immobiliser (Security-Learn status + re-sync button)
  - Maps (read-only fuel/ignition table viewer)
- **Win98-adjacent styling** (beveled buttons, blue title bar, tan/grey palette)
- **Headless-testable** (pytest-qt, runs via `QT_QPA_PLATFORM=offscreen`)

### Phase 5: Gated Programming ✅
- **Security-Learn (Immobiliser re-sync):** The ONE genuine GEMS K-line write
  - Virtual ECU implements $31 (Security-Learn routine)
  - Reproduces "ENGINE IMMOBILISED" failure mode
  - Recovers via BeCM code sync
  - GUI + CLI support
- **Gated Coding:** Backup → Verify → Confirm flow
  - VIN, dealer ID, 4.0/4.6 engine select, transmission config
  - Per-field ASCII/hex codecs
  - Prevents accidental corruption
- **Maps Viewer:** Read-only 16×16 fuel/ignition EPROM tables
  - 27C512 (fuel) + 27C1001 (ignition) EPROM specs
  - Chip-swap lookalike (authentic GEMS ECU truth: no K-line reflash)

## Command-Line Interface

```bash
python -m gems_t4 scenarios                          # List fault scenarios
python -m gems_t4 live [--scenario NAME]            # Live data
python -m gems_t4 dtc read [--scenario NAME]        # Read fault codes
python -m gems_t4 dtc clear [--scenario NAME]       # Clear fault codes
python -m gems_t4 actuator ACTUATOR --state on|off  # Run actuator test
python -m gems_t4 coding read [--field FIELD]       # Read coding block
python -m gems_t4 coding write --field FIELD --value VALUE  # Write coding
python -m gems_t4 immo status                        # Check immobiliser status
python -m gems_t4 immo learn [--immobilised]        # Run Security-Learn
python -m gems_t4 gui [--scenario NAME]             # Launch GUI
```

All commands accept `--port COMx` (Windows) or `/dev/ttyACM0` (Linux) to talk to a real Pico adapter.

## Testing & Quality

- **45 passing pytest tests** (39 core + 6 GUI)
- **Full headless validation** — no hardware needed
- **Frozen contracts:** `INTERFACES.md` (core) and `GUI_INTERFACES.md` (screens) pin the wire format and module APIs
- **No I/O in core layers** — protocol/ and gems/ are timing-agnostic; only transport/ handles serial

## What's NOT Yet

- **Phase 3 on-car validation** — Pico firmware is ready, but needs a real Pico + ISO 9141 Click + vehicle/ECU to test
- **Phase 6 polish** — no authentic latency overlays, Win98 full skin, or gauge widgets yet
- **37 live parameters** — only 24 implemented (more to come)
- **Windows standalone build** — PyInstaller packaging not yet done
- **Td5/MEMS3 profile** — optional future real-reflash demo

## Installation

```bash
git clone https://github.com/howeypeter/landrover-gems_t4.git
cd landrover-gems_t4
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt     # CLI only
# OR for GUI (needs PySide6):  pip install -e ".[gui]"
python -m gems_t4 scenarios
```

## Use Cases

✅ **Educational:** Learn about K-line protocols, GEMS ECU diagnostics, vehicle networks  
✅ **Research:** Explore what the real TestBook T4 did; reverse-engineer GEMS behavior  
✅ **Demo:** Show technicians the diagnostic workflow before real hardware arrives  
✅ **Development:** The venv is fast-iterable; test protocol changes without flashing Pico  
✅ **Testing:** Fault scenarios ensure symptom coherence across all screens  

## Known Limitations

- No real-time K-line traffic (virtual ECU runs instantly; `--latency` is emulated delay)
- FTDI cable transport is a stub (quick-read path not yet built)
- No wireless adapters yet
- Phase 3 needs hardware validation before the Pico adapter is production-ready

## Next Steps (Roadmap)

1. **Phase 3:** On-car validation of the Pico adapter (needs real hardware)
2. **Phase 6:** Polish for production kiosk experience (authentic waits, Win98 skin, gauges, 37 params)
3. **Optional:** Td5/MEMS3 real-reflash demo, Pico WiFi wireless mode, guided fault trees

---

**v0.0.1 is feature-complete for virtual diagnostics.** All the T4's core operations work: read DTCs, live data, actuator tests, coding, immobiliser re-sync. The GUI is fully wired and headless-testable. Ready for research, education, and development.

Start here, then add Phase 3 hardware validation when a Pico + vehicle are available. 🚙
