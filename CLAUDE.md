# CLAUDE.md — LandRoverV1

**This directory is the project home. Always save project files here** —
specs, diagrams, docs, code, and working notes all live under
`C:\Users\howey\OneDrive\Documents\Claude\Projects\LandRoverV1`.

## What this project is

A **UI/workflow simulator of the Rover/Land Rover TestBook T4 Mobile** dealer
diagnostic tool: a software recreation of its touchscreen interface and
diagnostic workflows, backed by a **fake/emulated ECU** — no car or adapter
required. Vehicle coverage centres on the **user's own vehicle type: a GEMS-era
Land Rover (Lucas/SAGEM GEMS V8, 1995–early 1999)** — this is what the user wants
to research. Other models are generic/representative. Started July 2026.

**As of 2026-07-06 the project has expanded**: beyond the UI simulator, the user
wants to build a **real Python CLI tool that can talk to and "program" a GEMS
ECU**, T4-style. A six-agent research sweep produced a full technical dossier —
see `memory/research/` (start with `SYNTHESIS.md`). Two findings reshape scope
(next two subsections).

### ⚠️ Vehicle correction: GEMS ≠ Discovery 2

GEMS (Lucas/SAGEM) was fitted to the **P38 Range Rover 4.0/4.6 (1995–early
1999)**, the **Discovery Series I V8i (1996–early 1999)**, and the Defender 90
NAS V8 (1997). The **Discovery 2 petrol V8 was ALWAYS Bosch Motronic M5.2.1
"Thor" — never GEMS** (Disco 2 launched after the GEMS era). So a genuine GEMS
truck is a **P38 or a Discovery 1**, not a Discovery 2. **Open question for the
user: confirm the actual vehicle** — this sets the whole protocol/data target.
"GEMS or Thor?" is the authentic first fork in VIN identification.

### ⚠️ "Programming" a GEMS ECU means three things — only one is over the wire

GEMS = Intel 87C196KC (dual-CPU) + **two socketed UV-EPROMs** (27C512 fuel maps,
27C1001 ignition + code). It has **no flash and cannot be reflashed over the
K-line** — unlike the later Td5/MEMS3 (AMD flash, fully documented by Revill).
So "program the ECU like the T4 did" splits into:
1. **Maps/calibration** → physical **EPROM chip swap** on the bench; no K-line
   path ever existed. Emulate as a chip-swap/lookalike, not a real reflash.
2. **Immobiliser "Security Learn"** → the ONE genuine K-line write; re-syncs
   BeCM↔ECM (the "ENGINE IMMOBILISED" recovery). Exact GEMS bytes not public.
3. **Config/coding** (VIN last-6, dealer ID, 4.0/4.6 select, transmission) →
   small read/edit/write Settings fields. Full VIN/EKA/market coding lives in
   the **BeCM**, not the engine ECU.

Full GEMS *diagnostics* (init, live data, DTCs, actuators, adaptations, config
writes, immobiliser sync) are all implementable/emulatable — only "reflash the
maps over the wire" is off the table, because it never existed for GEMS.

---

## What the real T4 was: Hardware and software

- **System**: Dealer diagnostic tool for Rover Group / MG Rover / Land Rover,
  built by **Omitec**. A laptop running **RDS software (4.04, later 5.06 "T4
  Lite")** that **takes over the machine completely** — on boot you get the RDS
  screen, never Windows. Ran on Win98 (slow but stable), later XP.
- **Connection chain**: Laptop → LAN port (+ modem port) → **VCSI interface box**
  (a demultiplexer with XILINX XC3064 FPGA card) → lead → vehicle **J1962
  connector** (16-pin, under dash). Car talks **ISO 9141** (~10.4 kbit/s,
  half-duplex, tester-initiated). Old TestBook was serial-only/not OBDII
  compliant; T4 was. With the LAN cable unplugged, "certain features were not
  available but basic diag worked."
- **Software versions**: RDS 4.04 has no USB support; **RDS 5.06 (T4 Lite)**
  added a configuration-menu option to select between LAN Unit and USB connector.
  Generic ISO9141 USB interfaces do NOT work — the T4 Mobile follows J2534
  passthru but its J1962 firmware is unique (cannot be replicated with an
  ELM327 or CANable).
- **Ediabas dependency**: Also required **Ediabas** (BMW diagnostics runtime —
  fits Rover 75/MG ZT's BMW parentage); widely believed to be deliberate
  dealer lock-in so the programs cannot be used outside the dealer network.
- **Version ID**: Emulator should report RDS **5.06 / T4 Lite** on boot and in
  About screens.
- **Self-tests**: Included operator system checks, e.g. a LAN card check
  reporting "present"/"not present" with the period disclaimer that the LAN
  facility "is intended for potential future developments in dealership systems,
  and is not currently in use" (quoting the real manual; this phrase is canon
  for authenticity).

## The T4 protocol and capabilities

Per Andrew Revill's MEMS3 reverse-engineering (https://andrewrevill.co.uk/MEMS3TestBookT4Support.htm):

- **Live data**: Service **$61** records carry live measures (unsupported IDs
  answer **$7f** with default values). The T4 exposes **~108 live measures**
  (vs ~15 on a generic OBD-II scanner):
  - Engine temps (coolant, oil, inlet air), pressures (inlet manifold)
  - Electrical (battery voltage, ignition state)
  - Engine operation (RPM, throttle angle, fuel injection timing)
  - Emissions (oxygen sensor data, catalyst state)
  - Ignition timing and coil charge times
  - Misfire detection and per-cylinder counts
  - Idle speed control parameters
  - Air conditioning and fan operations
  - Vehicle speed and gearbox status
- **Refresh rate trade-off**: ~20 samples/s watching one measure; degrading to
  one sample per ~2 seconds with all 108 selected. Selecting more gauges
  should visibly slow the update rate — this is authentic and part of the
  character.
- **Actuator tests**: Command various engine systems for testing; implement
  safety interlocks (won't disable fuel pump with engine running; injectors
  receive brief pulses only, not continuous control).
- **Service adjustments**: Blanket modifications to ignition timing (−6° retard
  to +3° advance) and idle speed adjustments for engine wear, carbon buildup,
  fuel quality.
- **Rover-specific features**: ZCS (alphanumeric configuration codes) programming,
  VIN coding, immobiliser status verification (Rover 75 / MG ZT).

## The vehicle side: Late-1990s Land Rover electronics

Representative vehicle: **P38 Range Rover 4.0/4.6 V8 with GEMS engine
management (1995–1998)** — the user's own vehicle type. Detailed reference in
`docs/land-rover-electronics.md`. Network diagram in
`diagrams/p38-gems-network.svg` — a consolidated view of both the diagnostic
K-line star topology and the point-to-point wiring for real-time coordination
(BeCM-centric message centre, EAS faults, immobiliser, outstations).

### GEMS in one paragraph

**GEMS** ("Generic Engine Management System", Lucas/Sagem) ran the Rover V8
4.0/4.6 in the P38 from launch until the 1999 model year, when Bosch Motronic
M5.2.1 ("Thor") replaced it. One ECM does fuel + ignition: hot-wire MAF,
distributorless wasted-spark coil packs. NAS GEMS trucks are genuinely OBD-II
compliant; the TestBook gets far more (full codes, live data, actuator drives)
over the same K-line. The ECM won't run without a coded mobilisation signal
from the BeCM — the "ENGINE IMMOBILISED" sync fault is a canon failure mode.
"GEMS or Thor?" is the first fork in every P38 engine procedure, so VIN-era
identification in the emulator is authentic, not pedantry.

### The headline: No CAN bus

A late-90s Land Rover has **no CAN bus**. Every ECU hangs off a **single shared
diagnostic wire** — the **ISO 9141 "K-line" on pin 7 of the J1962 OBD socket**
— running at ~10.4 kbit/s, half-duplex, tester-initiated. The TestBook addresses
each module individually over that one wire. It is a star for diagnostics only;
the modules do not talk to each other over it.

**CAN only arrives with the BMW-engineered L322 Range Rover in 2002.**

### Modules on board (GEMS P38 Range Rover)

| Module | Role | Address on K-line |
|---|---|---|
| GEMS ECM | 4.0/4.6 V8 fuel + ignition (Lucas/Sagem) | $10 (engine) |
| EAT ECU | ZF 4HP24 automatic gearbox | $F1 (transmission) |
| ABS ECU | Wabco ABS + electronic traction control | $74 (ABS) |
| EAS ECU | Electronic air suspension: height sensors, compressor, valve block | $78 (suspension) |
| BeCM | Body electrical Control Module — locks, alarm, immobiliser, lighting, relays | $80 (body) |
| Instrument pack | Gauges + message centre ("EAS FAULT", "SLOW 35 MPH") | Driven by BeCM serial link |
| SRS ECU | Airbags | $B0 (safety) |
| HEVAC ECU | Climate control (blend motors, "book symbol" fault indicator) | $B8 (climate) |

(Addresses are representative; exact values vary by region/year.)

**The BeCM is the P38's defining feature** — a large body computer under the
driver's seat that runs nearly all body electrics directly (vs the Discovery
2's distributed BCU + IDM), drives the message centre over a serial datalink,
talks to door outstations over serial links, and mobilises the engine ECM.
Canon failure modes: refusing to sleep (flat battery), BeCM/ECM immobiliser
sync faults ("ENGINE IMMOBILISED").

### How modules coordinate while driving

**No bus chatter — dedicated point-to-point wires and slow serial links:**

- **BeCM ↔ instrument pack**: Serial datalink carrying gauge data and
  message-centre text — many driver warnings are BeCM messages, not lamps.
- **BeCM → GEMS ECM**: Coded immobiliser mobilisation signal. No code, no
  start.
- **BeCM ↔ door outstations**: Serial links for windows/locks/switches.
- **EAT ↔ GEMS ECM**: Torque reduction request during gear shifts.
- **ABS → ECM/instruments**: Hardwired road-speed pulse signal.
- **EAS ECU → message centre (via BeCM)**: Fault and height-mode messages.
- Everything else (A/C request, fuel gauge) is plain analogue or switched 12V.

**Result**: Every system is an island. The virtual transport should model "one
K-line, tester polls each ECU by address" and emphasize that the
vehicle-configuration step (which systems are fitted) matters because there's no
gateway module or network discovery.

### OBD-II is only half-true

- **Petrol V8s** (esp. North American spec GEMS trucks) are genuinely OBD-II
  compliant — a generic scanner can read emissions-related engine data over
  ISO 9141-2.
- **Everything else on the truck** (EAS, BeCM, ABS, HEVAC, SRS — and the Td5
  diesel on other models) speaks proprietary Rover/Lucas protocols on that same
  K-line — which is precisely why a TestBook was needed, and why generic ELM327
  adapters see almost nothing beyond the engine.

### Era variations

- **Discovery 2** (1998+): Td5 diesel or Bosch Motronic V8 (never GEMS);
  distributed body control (BCU + IDM) instead of a BeCM; adds SLABS
  (ABS + self-levelling) and ACE (active cornering). The existing `d2-*`
  diagrams show this truck.
- **Range Rover Classic / Discovery 1 V8**: Lucas **14CUX** fuel-only injection
  with a distributor — the generation before GEMS.
- **Freelander 1** (1997+): Same no-CAN, K-line-star pattern with fewer modules.
- **Defender**: Barely computerized until the Td5 engine (1998) brought an ECM.

## Design pillars (what "good" looks like)

1. **Kiosk, not app** — Full-screen appliance feel; everything driven through
   chunky touch targets and the tick/cross/back button bar. Takes over the
   window on boot.
2. **Guided, not free-form** — VIN-first vehicle identification that determines
   which systems are fitted/enabled; wizard-shaped step-by-step workflows, not a
   PID browser. A technician is walked through, not handed 4000 choices.
3. **Deep live data with realistic bandwidth** — Many parameters (aim for ~40–60
   to start); selecting more gauges visibly slows the update rate from ~20/s to
   ~1 every 2s. This bandwidth trade-off is part of the charm.
4. **Actuator tests whose *refusals* are emulated** — "Test not available —
   engine running" is as characterful as the tests themselves.
5. **The waiting** — "Communicating with ECU… please wait" progress bars;
   authentic latency (make it configurable/skippable for impatient users). ISO
   9141 tester-initiated half-duplex is slow; don't make it instant.
6. **Rover party pieces** — Service adjustments (ignition −6°…+3°, idle offset),
   ZCS/immobiliser screens, Toolbox self-tests (LAN card "present" with the
   exact disclaimer, VCI check, touchscreen calibration), LAN-vs-USB
   configuration option in menus.
7. **P38 party pieces** — EAS height/calibration screens, BeCM
   settings/immobiliser sync (with the "ENGINE IMMOBILISED" failure mode),
   message-centre text mirroring the active faults.

## Spec decisions locked in

- Emulate **RDS 5.06 / T4 Lite** specifically.
- **Toolbox/Configuration is a real feature**: Self-tests and VCI selection,
  quoting the authentic messages from the manual.
- **Virtual transport models the full chain**: Laptop → VCSI → J1962 lead → ECU,
  each link with its own status. Unplugging a virtual link produces authentic
  failure modes (e.g. "VCI not responding" if VCSI is simulated as disconnected).
- **Virtual ECU is separate from the UI**, speaks T4-style request/response
  records ($61/$7f), so fault scenarios drive coherent symptoms across screens.
  Transport is swappable — same I/O-isolated-from-formatting philosophy that
  makes code testable without hardware.
- **Fault scenarios** (~4: healthy vehicle / failed coolant sensor / cylinder-3
  misfire / lambda heater open circuit) make the read → diagnose → clear
  workflow meaningful. Each scenario produces consistent symptoms across all
  screens. All four fit the GEMS petrol V8 naturally (better than the Td5,
  which has no lambda sensors).
- **Fidelity is era-faithful, not pixel-accurate** — No good RDS screenshots
  exist (even Revill photographed screens with a phone). Target: Win98-dealer-tool
  aesthetic (800×600, beveled buttons, tick/cross bar, tan/grey palette), but
  layouts are reconstructed from the protocol and UX patterns, not photographic
  accuracy.

## Proposed v1 scope (user decision pending)

**Flow**: Boot → VIN entry/vehicle ID → system selection → fault codes
(read/clear with confirmation prompts) → live data (with gauge-count→refresh-rate
trade-off) → 2–3 interlocked actuator tests (e.g. fuel pump prime, injector
pulse, idle hunt), driven by the fault scenarios above. Programming/ZCS screens
as static lookalikes for now.

**Open questions (awaiting user confirmation)**:

1. **Fidelity dial**: Full nostalgia (authentic boot, fake latency, the waiting,
   Win98 aesthetic) or lightly modernized rendering? Recommendation: **full
   nostalgia** — the charm *is* the point.
2. **V1 scope sign-off**: Is the flow above (VIN → systems → codes → live data
   → actuator tests) right? Too much, too little?
3. **Guided fault trees or menu-driven?**: Include at least one full guided
   diagnostic procedure (e.g. "coolant sensor implausible → check connector →
   measure resistance → replace → clear codes") or stay menu-driven for v1?

## Sources and research notes

- **Andrew Revill** — MEMS3 TestBook T4 support (protocol-level detail):
  https://andrewrevill.co.uk/MEMS3TestBookT4Support.htm. This is the most
  detailed public reverse-engineering of the real system; it documents the exact
  byte positions, bit meanings, service codes, and live-data records. **Caveat:
  Revill documents MEMS3 (Rover K-series), not GEMS** — the emulator uses
  T4-style $61/$7f records as a faithful stylization unless GEMS-specific
  protocol documentation turns up.
- **RAVE manual/CD** — official Land Rover workshop documentation covering the
  P38 (GEMS diagnostics, pinouts, fault codes, BeCM/EAS procedures). The
  authoritative service source for the user's vehicle; worth obtaining.
- **"Rover T4" thread, MG-Rover.org** (user's saved PDF:
  `C:\Users\howey\Downloads\Rover T4 _ MG-Rover.org Forums.pdf`, July 2026).
  Forum posts from 2005–2010 covering hardware setup (RDS 4.04 vs 5.06, serial
  vs USB interfaces), first-hand experience (software "operates outside of
  Windows"), system self-tests (LAN card check quoting), and attempts to build
  open-source replacements.
- **Note**: mg-rover.org and rangerovers.net block automated fetching (402 via
  Tollbit). If the user has more screenshots or details, ask them to save and
  provide; don't retry WebFetch.

## Files in this directory

- `CLAUDE.md` — This file, the spec of record. Every detail the next bot needs.
- `docs/land-rover-electronics.md` — Standalone reference on late-90s Land Rover
  electronics, now centred on the GEMS P38; modules, protocols, and why there's
  no CAN bus. Discovery 2 retained as an era variation.
- `diagrams/p38-gems-network.svg` — Consolidated diagnostic + operating network:
  TestBook → VCSI → J1962 → K-line diagnostic star to all eight ECUs. Visually
  distinguishes **integrated real-time coordination network** (GEMS, EAT, ABS,
  EAS, BeCM hub, Instruments, door outstations) from **isolated systems** (SRS:
  K-line only for safety-critical crash detection; HEVAC: K-line + analogue 12V
  for climate). All verified by three independent agents (rendering, components,
  connections).
- `memory/` — Project-local memory (this project's canonical memory; never mix
  with other chats' memory). Includes `memory/research/` — the 2026-07-06
  six-agent GEMS dossier (SYNTHESIS.md + gems-hardware, gems-data-catalog,
  kline-protocols, opensource-tools, hardware-interfaces, python-architecture).

## Next steps for implementation

1. **Confirm the three open questions above** (fidelity, v1 scope, fault trees).
2. **GEMS research** — fault code tables, live-data parameter list, actuator test
   set. RAVE manual is the authoritative source for the user's vehicle. This is
   the stated research interest.
3. **Design the virtual ECU** — a state machine with a warm-up curve, idle hunt,
   and the four fault scenarios. It responds to $61 requests with the correct
   byte format.
4. **Build the UI shells** — Win98-styled screens for VIN entry, system
   selection, fault code list, live gauges (with refresh-rate trade-off),
   actuator tests, service adjustments, and Toolbox self-tests.
5. **Wire them together** — The UI speaks $61/$7f to the virtual ECU; the
   virtual ECU returns data; symptoms flow consistently across screens.
6. **Populate the fault scenarios** — Each scenario (healthy, coolant failure,
   misfire, lambda heater) produces coherent symptoms: specific fault codes,
   live data anomalies, actuator test failures.

## Tech stack — Python + PySide6, Windows desktop (decided 2026-07-06)

Scope narrowed by the user: **Windows laptop only, wired USB serial (no BLE), no
iPhone/Android.** The hacking is done on a Windows laptop plugged into the car.
That removes the only reason we'd left Python (iPhone), so the tool is **Python**
— the best environment for interactive reverse-engineering over serial — with
**PySide6 (Qt)** for the GUI and **Rich** for the CLI/dev phase. (Decision arc:
Python → Flutter/Dart when iPhone was a target → back to Python once iPhone/BLE
were dropped. See `memory/tech-stack-decision.md`.)

- **Four strict layers as Python packages**:
  - `gems_core/` — pure-Python, no UI/IO leakage: protocol framing (KWP2000/
    ISO-14230), GEMS services (DTCs, $61 live data, actuators, coding), and the
    **virtual ECU**. The engine; runs in CLI, tests, and the GUI.
  - `transport/` — the only Python code that touches I/O (the *timing* lives in
    the adapter firmware, not here). Implementations: **Virtual** (in-memory →
    virtual ECU) and **PicoAdapter** via `pyserial` — a USB-CDC link to the Pico
    smart adapter (**canonical real transport**). A raw **FTDI KKL cable**
    transport is a secondary quick-start/read option. **No BLE.**
  - `firmware/` — Raspberry Pi **Pico (RP2040)** sketch (Arduino C++). Owns the
    K-line: 5-baud/fast init, P1–P4 byte timing, half-duplex echo cancellation,
    frame-by-inter-byte-timeout. Exposes a simple **length-prefixed host protocol
    over USB-CDC** so Python stays timing-agnostic. **Pico = timed K-line byte
    pipe; Python = all KWP/GEMS logic** (protocol R&D stays in fast-iterate Python;
    no reflash to change behaviour). RP2040 PIO can clock the 10.4 kbaud UART +
    5-baud init precisely. Refs: muki01/OBD2_KLine_Library, iwanders/OBD9141.
  - `app/` — presentation: a **Rich CLI** now (dev/hacking bench), a **PySide6
    GUI** later (the Win98 T4 kiosk skin). Both thin consumers of `gems_core`.
- **Load-bearing seam**: `KwpClient(transport)` takes a real serial transport OR
  the `VirtualTransport` → whole stack testable off-car (udsoncan-shaped
  Connection/Client split).
- **Libraries**: `pyserial` (+ `pyftdi` if bit-bang 5-baud init is needed),
  `rich` (CLI), **`PySide6`** (GUI), `pytest`. Package to a Windows `.exe` with
  PyInstaller. Study ecu-diagnostics (Rust), memsfcr (Go), libcomm14cux (C) for
  the Rover-adjacent logic to port.
- **GUI = PySide6/Qt**: custom-painted beveled widgets + QSS for the 800×600
  Win98 kiosk, `QPainter` gauges for live data, fullscreen kiosk mode.
  (Alternative weighed: pywebview + `98.css` for pixel-authentic chrome via
  HTML/CSS — rejected to stay single-language and keep realtime gauges snappy.)
- **Hardware, wired only** (see `memory/research/hardware-interfaces.md`):
  - **Primary rig: Raspberry Pi Pico *or* Pico 2 + MikroE ISO 9141 Click (L9637D)
    over USB** — the smart adapter (modern VCSI equivalent). Both boards run
    the identical firmware unmodified (the sketch only uses the portable
    Arduino API — `Serial`, `Serial1`, `pinMode`, `digitalWrite`, `delay`,
    `millis` — which `arduino-pico` implements the same on RP2040 and RP2350);
    only the build's `--fqbn` target differs (`rpipico` vs `rpipico2`). Either
    is fine for reads AND writes (immobiliser sync, coding), immune to USB
    latency jitter. Canonical transport. BLE dropped → a plain (non-W) Pico is
    fine, no wireless needed for the wired path.
  - **Quick start: genuine FTDI KKL 409.1 cable** (`pyserial`) — cheap, good for
    first reads and capturing traffic; marginal for writes.
  - **Planned, not yet built: Pico 2 W wireless (WiFi) mode, read-only.** Decided
    2026-07-07: eventually add an opt-in wireless transport for live-data/DTC
    monitoring only (no coding/actuator/Security-Learn writes over it — those
    stay wired-only). Likely shape: WiFi/TCP reusing the same host-protocol
    framing (not BLE — BLE's small MTU would need chunking the 255-byte frames
    for no benefit, and BLE was already ruled out for ECU work generally); the
    write-refusal enforced in the Python `KwpClient` by checking a
    `Transport.is_wireless` flag, not in firmware (firmware stays a dumb timed
    pipe). Do not build a Pico W / Pico 2 W adapter yet — not supported until
    this lands.
- **Build the virtual ECU first**; **every ECU write gated**: backup + verify +
  checksum + session/security + precondition interlocks + dry-run + confirmation.

### Recommended phased build

1. `gems_core` + virtual ECU + Rich CLI; healthy scenario; read DTC + one $61
   measure end-to-end (`python -m gems_t4 live --fake`). ✅ DONE (2026-07-06)
2. Protocol depth on the fake: full $61 map, DTC read/clear, session/tester-
   present, actuators + refusal interlocks, all four fault scenarios, bandwidth
   model, full `pytest` suite. ✅ DONE (2026-07-06)
3. Hardware bring-up: define the **Pico↔host protocol**; write the **Pico
   firmware** (init + timed K-line pipe) and the Python **PicoAdapter** transport;
   validate against a real ECU (FTDI cable for early reads); capture K-line traces
   as fixtures; contract-test virtual and Pico transports against one suite.
   ◑ PARTIAL: host protocol + Pico firmware + PicoAdapter built & unit-tested vs a
   fake serial; runs on Pico or Pico 2 (same firmware, build target only differs;
   2026-07-07); FTDI transport is a documented stub; on-car validation pending HW.
3b. **Future, not started:** Pico 2 W wireless (WiFi) read-only mode — see the
   "Planned, not yet built" note under Tech stack → Hardware above. Do not begin
   until explicitly picked up.
4. **PySide6 GUI shell** over the same `gems_core` — Win98 kiosk, live gauges.
   ✅ DONE (2026-07-07): `gems_t4/app/gui/` — a Qt-free `Backend` facade
   (`app/backend.py`) + `KioskWindow`/`Screen` shell + 7 screens (boot, vehicle
   ID + scenario select, system menu, fault codes, live data with the gauge-count
   → refresh-rate trade-off, actuator tests with refusals, toolbox self-tests
   quoting the LAN disclaimer). Win98 QSS. Launch: `gems_t4 gui [--scenario X]`
   or `python -m gems_t4.app.gui`. Contract in `GUI_INTERFACES.md`; built by a
   3-agent fan-out against 3 reference screens I wrote. Headless-tested
   (offscreen) with pytest-qt.
5. Programming, gated: coding + Security-Learn first, then the map-editor
   lookalike; (optional) a Td5/MEMS3 profile for a *real* documented reflash demo.
   ✅ DONE (2026-07-07): **Security-Learn** immobiliser re-sync (the one genuine
   GEMS K-line write) — `gems/immobiliser.py` + virtual-ECU `$31` routines +
   `immobilised=True` reproduces the canon "ENGINE IMMOBILISED" non-start and
   recovers it. **Gated coding** — `gems/programming.py` (backup + verify +
   confirm gates) now wired through the backend with ASCII/hex codecs. **Map
   editor lookalike** — `gems/maps.py` (27C512 fuel / 27C1001 ignition EPROM
   facts + viewable 16×16 fuel/ignition tables, read-only with the "no K-line
   reflash, bench chip-swap" note). All exposed via CLI (`coding read|write`,
   `immo status|learn`) and GUI (programming sub-menu → coding / immobiliser /
   maps screens). Td5/MEMS3 real-reflash profile still optional/not started.
6. Polish → full Win98 T4 skin; PyInstaller Windows build.
   ✅ DONE (2026-07-07): **Real gauge widgets** — `app/gui/widgets.py`
   (QPainter `DialGauge`/`BarGauge`/`LcdReadout`) + `app/gui/gauge_specs.py`
   (per-param scale/redline/style); the live-data screen renders a grid of
   analog gauges (was a table), keeping the gauge-count → refresh-rate trade-off.
   **"The waiting"** — `app/gui/wait.py`: "Communicating with ECU - please wait"
   overlay + `KioskWindow.run_with_wait` running backend ops on a background
   worker thread with an enforced minimum wait (click to skip); wired into
   vehicle-id, fault-codes, actuators, immobiliser, coding. `GEMS_T4_INSTANT=1`
   env var / `gui --instant` flag = synchronous instant mode (tests set it in
   `tests/conftest.py`). **Full Win98 skin** — style.py rebuilt on per-side bevel
   fragments (white top-left / dark bottom-right), chunky 16px scrollbars, combo
   drop-downs, tooltip (#ffffe1), checkbox/radio, dotted focus, segmented
   marching-blocks QProgressBar; arrow/check glyphs are tiny PNGs rasterised at
   import (pure-QSS border-triangles render as black rectangles — known Qt
   gotcha); gauges got bevel rings/sunken tracks to match. Verified against
   real screenshots (native platform; offscreen has no fonts). **$61 params
   24 → 37** — injector PW, coil charge, purge duty, fuel pump, run time (fed
   from sim clock), per-cylinder misfire counts 0x20–0x27 (misfire_cyl3 puts
   the count on cyl 3 only; 1-byte counters saturate at 255). **Windowed exe**
   — `packaging/_entry_gui.py` + second EXE in `gems_t4.spec`: one
   `dist/gems_t4/` bundle now holds console `gems_t4.exe` AND no-console
   `gems_t4_gui.exe`. **E2E QA** — `tests/test_gui_e2e.py` (6 tests through the
   production `build_window` wiring: full nav tour, misfire diagnostic session,
   gauge sweep + bandwidth monotonicity, refusal propagation, overlay
   lifecycle, all-screen paint smoke). Built by a 5-agent fan-out (two stalled
   mid-stream and were resumed — same failure mode as Phase 1-2).

### Build status

**Where the project stands (2026-07-07):** Phases **1, 2, 4, 5, 6 complete**;
Phase 3 (Pico adapter) built + unit-tested but needs real hardware for on-car
validation. **123 passing tests** (or "74 passed, 10 skipped" without the
PySide6 `[gui]` extra — 10 GUI test files; both counts verified empirically).
Runs via `python -m gems_t4 <cmd>` or `gems_t4` after `pip install -e .`; GUI
via `gems_t4 gui` (needs `[gui]`; `--instant` skips the waits). Python 3.14
venv at `.venv/`. ~70 Python files, 11 GUI screens, 37 live-data params.
Remaining polish candidates (not started, optional): windowed-exe icon/version
resources, more guided fault trees, Td5/MEMS3 real-reflash profile.

**Quick start & known limitations (2026-07-07):**
- **Launcher scripts:** `launch_gui.bat` (quick launch) and `create_shortcut.ps1`
  (create desktop shortcut on Windows) are in the project root for convenience.
- **PyInstaller bytecode cache gotcha:** If the bundled exe (`dist/gems_t4/gems_t4_gui.exe`)
  doesn't reflect the latest source changes, run from the venv instead:
  `python -m gems_t4 gui`. This is a known Qt/PyInstaller interaction where
  bytecode caches persist even after `--clean` rebuilds. To force a fresh exe,
  manually delete `packaging/build/` and `dist/` before rebuilding.
- **GUI waits:** By default, `gui` shows the period-authentic "Communicating with
  ECU - please wait" overlay (click it to skip). Use `gui --instant` to disable
  waits entirely, or set env var `GEMS_T4_INSTANT=1` (used by all tests for
  determinism).

**Phase 5 (2026-07-07):** programming/coding/immobiliser/maps — `gems/
immobiliser.py` (Security-Learn), `gems/maps.py` (chip-swap lookalike), `gems/
programming.py` codecs, virtual-ECU `$31` + `immobilised` flag, backend methods,
CLI (`coding read|write`, `immo status|learn`), and 4 GUI screens via a 3-agent
fan-out against `GUI_INTERFACES.md`. All validated end-to-end headless.

### Repository / git state (2026-07-07)

- Git repo, branch **`v0.0.1`** (also `main`, `origin/main`). **Only `README.md`
  is committed** (a GitHub stub) — **everything else is untracked**, safe on disk
  but NOT in git history. First real commit still pending (`git add -A && git
  commit` on `v0.0.1`). Don't run destructive git (`reset --hard`/`clean`) before
  committing — it could wipe untracked work.
- `.gitignore` (excludes `.venv`, caches, `__pycache__`, egg-info, OneDrive junk,
  firmware build output) and `.gitattributes` (`* text=auto eol=lf` — pins LF to
  silence Windows `core.autocrlf=true` CRLF churn) are in place.
- **Two READMEs**: `README.md` = concise Markdown GitHub landing page with prominent
  links to the HTML docs; `README.html` = full styled docs. GitHub can't render
  `.html` inline, so `README.md` links use **htmlpreview.github.io** (zero-setup
  proxy that renders `https://htmlpreview.github.io/?https://github.com/...`)
  to show the rendered pages. Links reference the **`main` branch** (target merge
  destination), not version branches. Ideal future: fully dynamic URLs via GitHub
  Pages (always resolves to the default branch without hardcoding) or a CI workflow.
  Can't embed styled HTML into .md (GitHub strips CSS). Keep them roughly in sync.
  **Gotcha:** OneDrive/editor keeps re-encoding `README.md` to UTF-16 — re-convert
  to UTF-8 if `file README.md` shows UTF-16.
- Full detail in `memory/repo-git-state.md`.

**GUI added 2026-07-07:** Phase 4 PySide6 kiosk done. Launch `gems_t4 gui`;
install with the `[gui]` extra (`pip install -e ".[gui]"`). GUI tests run headless
via `QT_QPA_PLATFORM=offscreen` (set in `tests/conftest.py`); each GUI test file
starts with `pytest.importorskip("PySide6")` so a plain `requirements.txt` install
gives "N passed, K skipped" not errors. Contracts: `INTERFACES.md` (core),
`GUI_INTERFACES.md` (screens).

**Fixed 2026-07-07:** the 4 GUI test files each start with
`pytest.importorskip("PySide6")` so `pytest` after a plain `pip install -r
requirements.txt` (no PySide6) gives a clean "45 passed, 4 skipped" instead of
collection errors. Verified against a genuinely clean disposable venv, not just
reasoning about it. Two ways to get the GUI tests running too:
`pip install -e ".[gui]"` or `pip install -e ".[dev]"` (adds pytest-qt) → "63
passed" either way.

Phases 1–2 complete and validated: **45 passing pytest tests, ~2,500 LOC**,
runnable via `python -m gems_t4` (or the `gems_t4` script after `pip install -e .`;
deps via `requirements.txt`), CLI working (`scenarios`/`live`/`dtc`/
`actuator`, `--fake` by default; `--port COMx` for the Pico). Built by a 6-agent
parallel sweep against a frozen `INTERFACES.md`; the agents hit a mid-stream API
error after ~half the modules, and the rest (client, livedata, actuators,
ecu_profile, programming, virtual_ecu, transports, CLI, all tests, firmware) was
finished by hand to the same contract. Package layout + usage: `README.md` is the
concise GitHub landing page; `README.html` is the full styled version (open in a
browser — GitHub can't render `.html` inline). Keep both roughly in sync when docs
change. Frozen seams in `INTERFACES.md` / `GUI_INTERFACES.md`.
