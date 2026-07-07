---
name: research-synthesis
description: Synthesis of the 2026-07-06 GEMS research project — key findings, the two headlines, and the recommended build path
metadata:
  type: project
---

# GEMS ECU Programming Research — Synthesis

Six-agent research pass, 2026-07-06. Full detail in the sibling research files;
this is the decision-level summary.

## TWO HEADLINES (both need user awareness)

### 1. "Discovery 2 petrol with GEMS" is almost certainly a mistake
GEMS (Lucas/SAGEM) = **P38 Range Rover 4.0/4.6 (1995–early 1999)** and
**Discovery SERIES I V8i (1996–early 1999)** and Defender 90 NAS V8 (1997).
**Discovery 2 petrol V8 was ALWAYS Bosch Motronic M5.2.1 "Thor" — never GEMS.**
Disco 2 launched after the GEMS era ended. If the user's truck is genuinely
GEMS, it's a **Discovery 1 or a P38**, not a Disco 2. NEEDS USER CONFIRMATION —
this determines the entire protocol/data target. See [[research-gems-hardware]].

### 2. GEMS cannot be reflashed over the port — "programming" means 3 things
GEMS = Intel 87C196KC (or 68HC11 per one source) + two socketed UV-EPROMs
(27C512 fuel maps, 27C1001 ignition+code). NO flash. So "program the ECU like
the T4 did" splits into:
- **(a) Maps/calibration** → physical EPROM chip swap on the bench. NO K-line
  path. The real T4 had no GEMS map reflash. An authentic emulator should NOT
  offer "reprogram calibration" for GEMS (present it as a chip-swap lookalike).
- **(b) Immobiliser "Security Learn"** → the ONE genuine K-line write. Re-syncs
  BeCM↔ECM ("ENGINE IMMOBILISED" recovery). Exact GEMS bytes not public.
- **(c) Config/coding** (VIN, dealer ID, 4.0/4.6 select, transmission) → small
  read/edit/write Settings fields. VIN/EKA/market coding proper lives in the
  **BeCM**, not the engine ECU.

This is GOOD news for the project: full GEMS *diagnostics* (init, live data,
DTCs, actuators, adaptations, config writes, immobiliser sync) are all
implementable/emulatable. Only "reflash the maps over the wire" is off the table
— because it never existed for GEMS.

## The public-knowledge gap
GEMS has **no open-source protocol library** and its exact K-line command bytes
are **not publicly documented**. The closest byte-level template is Bourassa's
reverse-engineered **MEMS 1.6** single-byte-echo protocol; the closest
service-model is Revill's **MEMS3** $61/$7F records; neither is GEMS-verified.
So the virtual ECU can define its own coherent GEMS dialect — there's no
reference to conform to, only patterns to stay faithful to.

> **Language settled (2026-07-06): Python + PySide6, Windows-only, wired serial,
> no BLE** — see [[tech-stack-decision]]. (Brief Flutter/Dart detour while iPhone
> was a target; reverted when iPhone/BLE dropped.) The Python/pyserial build path
> below is the live plan; GUI is PySide6; the real transport is the **wired FTDI
> cable or a Pico/MCU over USB** (no BLE).

## Recommended build path (Python + PySide6, Windows desktop)

**Protocol/data model** (emulate faithfully, stylize where undocumented):
- Transport: single K-line, 8N1, tester-initiated, half-duplex, **self-echo**;
  support 10.4kbaud (ISO/KWP) + 9600 (Rover-native).
- Init: three pluggable strategies — 5-baud slow (addr 0x33 generic / 0x16
  Rover), fast init, Rover-native (CA 75 D0 echo handshake).
- Services: **$21/$61 live-data records + $7F negatives** (Revill model) for the
  ~35 documented GEMS params (3 tabs: Fuelling / Air&Idle / Engine-Others), plus
  **single-byte actuator/adjust commands** (Bourassa MEMS table) for fuel pump /
  coil / idle / ignition-trim.
- Timing: count bytes on the virtual wire → the fewer-gauges-faster bandwidth
  curve falls out naturally (P2 25-50ms, ~2s init, 10.4kbaud).
- Data: real GEMS DTC table (up-to-99MY block only — exclude 99MY+ Thor codes),
  ~35 live params with expected values + fail-safe substitutions, 5 output tests
  (relay/lamp-level), adaptation resets, Settings read-only/writable map,
  Security-Learn handshake with authentic failure. See [[research-gems-data]].

**Architecture** (see [[research-python-architecture]]):
- Four strict layers: `transport/` (only timing-aware) → `protocol/` (KWP
  framing, init, services, security) → `gems/` (DTCs, livedata, actuators,
  programming, scenarios) → `app/` (CLI now, Win98 UI later).
- Load-bearing seam: `KwpClient(transport)` takes real K-line OR `VirtualTransport`
  → whole stack testable off-car. Shape it like udsoncan's Connection/Client.
- Stack: pyserial + pyftdi (real) · borrow udsoncan abstractions · study
  KWP2000-CAN, ecu-diagnostics, memsfcr, libcomm14cux.
- Build the **VirtualEcu** first (state machine + fault scenarios speaking
  $61/$7F), develop entirely against it, add real hardware later.

**Hardware** (see [[research-hardware-interfaces]], for the "later" real-car phase):
- Start: genuine FTDI KKL 409.1 cable + pyserial, latency timer = 1ms.
- Build: L9637D transceiver + RP2040/ESP32 front-end owning K-line timing,
  framed serial to Python — same framed protocol as the emulator (swappable).
- The timing problem (5-baud init + inter-byte windows over jittery USB) is why
  a smart MCU front-end beats raw FTDI for anything write-related.

**Programming safety** (see [[research-python-architecture]]): every write behind
mandatory backup + verify-after-write + checksum + session/security gating +
precondition interlocks + dry-run + typed confirmation. Separate low-risk coding
from (emulated) flash.

## Phased plan
1. Skeleton + contracts, VirtualEcu + VirtualTransport, healthy scenario, read
   DTC + one $61 measure. `python -m gems_t4 live --fake` works.
2. Protocol depth on fake: full $61 map, DTC read/clear, session/tester-present,
   actuators + refusal interlocks, all 4 fault scenarios, bandwidth model.
3. Real transport — smart adapter (firmware init), contract suite vs bench ECU,
   capture real traces.
4. Real transport — dumb FTDI (pyftdi bit-bang init, latency=1ms, echo cancel).
5. Programming, gated: coding/Security-Learn first, then map-editor lookalike.
6. CLI polish → Win98 UI reuses same KwpClient/services.

## Open items for the user
- **Confirm the actual vehicle** (P38? Disco 1? Or a Thor Disco 2 mislabelled?).
- Save the Tollbit-blocked forum threads (rangerovers.net GEMS ROMs,
  landroversonly GEMS-8 remapping) — richest GEMS byte-level community knowledge.
- Decide whether to keep a "Td5/MEMS3" profile in scope later (the one genuinely
  flashable Rover engine ECU, fully documented by Revill) for a real reflash demo.

Related: [[research-gems-hardware]], [[research-gems-data]],
[[research-kline-protocols]], [[research-opensource-tools]],
[[research-hardware-interfaces]], [[research-python-architecture]],
[[gems-p38-focus]]
