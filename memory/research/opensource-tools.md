---
name: research-opensource-tools
description: Research findings — open-source and commercial software for Rover/GEMS diagnostics and programming
metadata:
  type: reference
---

# Software Survey: Rover/GEMS Diagnostic & Programming Tools

Research pass 2026-07-06.

## Strategic finding
**GEMS itself has NO open-source communication library.** Nobody has published a
GEMS K-line protocol stack. The open Rover ecosystem covers the **14CUX**
(GEMS's fuel-only predecessor) and the **MEMS family** (1.6/1.9/MEMS3) — GEMS is
the gap. GEMS is "chipped" (EPROM swap), not flashed, so GEMS "programming" =
EPROM-image editing on a bench, not over-the-port. The realistic over-the-wire
programming model to emulate is **MEMS3 (Revill's documented seed-key flashing)**;
a GEMS "flash" screen would be an emulation of the chip/coding workflow.

## Open-source projects (source available — study/reuse)

### 14CUX (Rover V8 predecessor) — Colin Bourassa, GPLv3
- **libcomm14cux** https://github.com/colinbourassa/libcomm14cux — C, reads ECU
  memory + live data (incl. read14cux CLI). Writes RAM only; fuel maps in ROM
  can't be changed this way. HIGH relevance — cleanest Rover-EMS read library to
  model a Python port on. Recurring pattern: read easy, ROM-write not exposed.
- **RoverGauge** https://github.com/colinbourassa/rovergauge — C++/Qt5, graphical
  live data over libcomm14cux. No write/tuning.
- **14cux-firmware** https://github.com/colinbourassa/14cux-firmware — rebuildable
  disassembly of the ECU firmware; reference for Rover V8 EMS internals.

### MEMS family — Bourassa + Jackson, GPLv3
- **librosco** https://github.com/colinbourassa/librosco — C, MEMS 1.6 live data +
  actuator tests (readmems CLI).
- **memsfcr** https://github.com/andrewdjackson/memsfcr — Go+HTML, MEMS 1.6-1.9,
  all data + fault codes + CSV; clears faults, adjusts idle/fuel trim/ignition
  advance. HIGH relevance — full working modern read→diagnose→clear→adjust loop.
- MEMS 1.6 protocol writeup: https://colinbourassa.github.io/car_stuff/mems_interface/

### KWP-71 / transport references — Bourassa
- **libiceblock** https://github.com/colinbourassa/libiceblock — C++, KWP-71
  block-transfer protocol.
- **torinoscan** https://github.com/colinbourassa/torinoscan — parameter data model.

### Generic K-line/ISO9141/KWP2000 stacks
- **muki01/OBD2_KLine_Library** https://github.com/muki01/OBD2_KLine_Library —
  C/C++ Arduino/ESP32, ISO9141 + ISO14230 slow/fast init, auto-detect. Clean
  K-line reference.
- **iwanders/OBD9141** https://github.com/iwanders/OBD9141 — C++, ISO9141-2 + KWP
  init, handles echo, ESP32 example + SN65HVDA195 schematic.
- **zkrx/obdpi** https://github.com/zkrx/obdpi — C, ISO9141 on Raspberry Pi
  (closest Linux/host K-line example).
- **aster94/Keyword-Protocol-2000** https://github.com/aster94/Keyword-Protocol-2000
  — C++ KWP2000, ships a Python ECU emulator.
- **jakka351/GenericDiagnosticTool** https://github.com/jakka351/GenericDiagnosticTool
  — C# J2534 passthru: KWP2000/UDS/OBD2/ISO9141/CAN, read DTCs/DIDs/memory/VIN.
  Flashing "planned" not implemented. No Rover.

### Map-editor ecosystem (LOW direct reuse — no Rover defs)
- RomRaider (GPL, Java) — no Rover/GEMS/MEMS. TunerPro (closed freeware, XDF
  format) — community GEMS-8 XDF attempts exist but none maintained. ECUFlash —
  no Rover. sostisoft/ecu-definitions — confirmed NO Rover defs. But XDF format
  is a good model for a GEMS map-editor (16×16 8-bit tables).

### Open TestBook/T4 replacement
**None found as a packaged project.** De-facto split between Bourassa's libraries
and Revill's MEMS3 tools. No project reproduces T4's multi-system K-line polling.
Genuinely open territory — the emulator fills a real gap.

## Andrew Revill's MEMS3 tools — most valuable resource (free, closed-source Delphi)
Best public protocol documentation for a Rover flashable ECU. Author permits
sharing executables.
- **MEMS Mapper** — remapping, live mapping, dual maps with live switching,
  bricked-ECU recovery. MEMS 1.9/3/2J + Land Rover Td5 MSB.
- **MEMS3 Flasher** — full read/write/clone over OBD-II, checksums auto-verified.
  THE real over-the-wire programming model.
- **MEMS3 Terminal** — monitors/decodes/logs OBD-II traffic (capture T4-style dialog).
- Index: https://andrewrevill.co.uk/MEMSToolsIndex.htm · Flasher:
  https://andrewrevill.co.uk/MEMSFlasher.htm
- Protocol detail (reusable): Service $61 live data, $7F unsupported, ~108
  measures; native ~9600 (BMW-like) + ISO 14230 fast-init 10400; seed-key
  reverse-engineered; actuator interlocks; cheap KKL 409.1 FTDI cable. **GEMS not
  covered by Revill** (MEMS/Td5 only).

## Commercial tools (context, esp. programming)
| Tool | GEMS | Programs GEMS? | Notes |
|---|---|---|---|
| TestBook/T4 (Omitec) | Yes | Config/coding + immobiliser, NOT map flash | VCSI→J1962, ISO9141 star |
| Nanocom Evolution (NCOM05) | Yes (licensed) | Read/clear faults, live, actuators, reset adaptives, settings — NOT firmware flash | Green OBD lead, K-line |
| Faultmate MSV-2 | Yes | Most capable: flash+EEPROM across LR, full BeCM reprogram (VIN+odo), Sync-Mate | Software modules→server→K-line |
| Hawkeye | Yes | Diagnostics; cannot program keys | OBD-II |
| Rovacom/Autologic | Yes | Pro T4 alternative, deep GEMS diag | K/L-line |
| GEMSFlash | — | Does NOT exist as a product | GEMS "programming" = physical EPROM swap (Tornado/Lloyd/Kingsley chips) |

Key takeaway: even Nanocom/Faultmate do GEMS diagnostics/service but do NOT flash
GEMS engine firmware over the port (it's UV-EPROM). Faultmate's flash targets
BeCM + other systems. MEMS3/Td5 are the flashable engine ECUs.

## Python building blocks
No Rover/GEMS Python library exists. Reusable: **pyserial** (foundation, raw
K-line, echo suppression), **python-OBD** https://github.com/brendan-w/python-OBD
(ELM327 layer + command/response architecture to model on), **udsoncan** (UDS/KWP
service abstraction, custom transports — wrap $61/$7F + seed-key), **python-can**
(only for 2002+ L322 CAN, not needed here), **ELM327-emulator (Ircama)**
https://github.com/Ircama/ELM327-emulator (KWP2000 ISO14230-2 processing,
reference emulator to test virtual ECU against).

## Bottom-line
1. READ/live/actuator/fault-clear fidelity: port from libcomm14cux + memsfcr +
   librosco (GPLv3) + Revill's $61/$7F + interlock semantics.
2. Plausible over-the-wire PROGRAM path: emulate MEMS3 (Revill: seed-key→boot→
   write) if you want authentic flash workflow.
3. GEMS specifically: no open library, no over-K-line flash — GEMS is EPROM.
   GEMS "programming" screen = emulate EPROM/coding/chip workflow + map editor
   over known tables (27C512 fuel 0x55D9/0x56E1, 27C1001 ignition ~0x13AEA, 16×16
   8-bit) TunerPro-XDF-style.
4. GEMS K-line protocol is publicly undocumented — the real reverse-engineering
   gap. Virtual ECU can define its own coherent GEMS dialog.

Related: [[research-gems-hardware]], [[research-kline-protocols]],
[[research-python-architecture]], [[research-hardware-interfaces]]
