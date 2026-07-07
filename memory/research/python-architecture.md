---
name: research-python-architecture
description: Research findings — Python architecture and library stack for a K-line GEMS ECU diagnostic + programming CLI tool
metadata:
  type: reference
---

# Python Architecture for a K-line GEMS ECU Tool

> **LANGUAGE CONFIRMED PYTHON (2026-07-06):** After a brief detour to Flutter/Dart
> (when iPhone was a target), the project settled on **Python + PySide6, Windows
> desktop only, wired serial, no BLE** — see [[tech-stack-decision]]. This file's
> architecture and library stack (pyserial, udsoncan-shaped seam, virtual-ECU-
> first, safety gates) are the live plan again. Two adjustments vs the original
> text below: **GUI is PySide6** (not "later Qt/web, TBD"), and the **BLE/smart-
> adapter-over-BLE path is dropped** — the smart MCU adapter, if used, connects
> over **USB-CDC serial**, not Bluetooth.

Research pass 2026-07-06 (agent 6 of 6). Target: modern open-source,
hardware-swappable, testable-without-a-car diagnostic + programming tool for a
Lucas/Sagem **GEMS V8** ECU speaking **ISO 9141 / KWP2000 over the K-line**.

## Key finding: almost nothing in Python targets raw K-line KWP2000

Mature libraries are all CAN/UDS-oriented. Best move: **reuse udsoncan's
transport/service abstraction where SIDs overlap, but write your own K-line
transport and your own GEMS service layer.** UDS ($22/$27/$7F etc.) is the
successor to KWP2000 and shares the request/response + negative-response shape
that matches the T4's $61/$7F records the project already committed to.

## Library landscape

| Library | Verdict | URL |
|---|---|---|
| **udsoncan** (pylessard) | PRIMARY reference / partial reuse. Clean `BaseConnection` transport-swap seam; UDS DTC/session/security/routine modelling directly instructive. Does NOT implement KWP2000 K-line init or ISO-14230 framing — you supply the K-line connection. MIT. | https://github.com/pylessard/python-udsoncan |
| **KWP2000-CAN** (EliasTuning) | CLOSEST prior art — Python, supports KWP2000 over serial/USB K-line, sessions, read/write memory, routine control, timing params. BMW/VAG-shaped. Study closely, possibly vendor parts. | https://github.com/EliasTuning/KWP2000-CAN |
| **pyserial** | FOUNDATIONAL — real transport rides on this. | https://github.com/pyserial/pyserial |
| **pyftdi** | For the 5-baud slow-init problem — bit-bang TX line control + latency param. | https://eblot.github.io/pyftdi/ |
| **ecu-diagnostics** (Rust) | Best DESIGN reference — implements KWP2000 AND UDS with a `Hardware` trait abstracting physical layer. Mirror its layering. | https://docs.rs/ecu_diagnostics |
| **Keyword-Protocol-2000** (aster94, C++) | Reference — ISO-14230/9141, ships a Python ECU emulator (precedent for virtual ECU). Source of init/checksum vectors. | https://github.com/aster94/Keyword-Protocol-2000 |
| **OBD2_KLine_Library** (muki01, C++) | Reference — clean ISO-9141 + ISO-14230 init handshake + timing to port to Python. | https://github.com/muki01/OBD2_KLine_Library |
| **ecu-simulator** (lbenthins) | Reference for virtual ECU (UDS/CAN, not reusable directly). | https://github.com/lbenthins/ecu-simulator |
| python-OBD | NO/minor — ELM327-only, read-only, can't reach proprietary GEMS measures. | https://github.com/brendan-w/python-OBD |
| python-can / can-isotp | NO — CAN-only; P38 has no CAN. BusABC pattern is a design template only. | https://python-can.readthedocs.io |

**Bottom-line stack:** `pyserial` + `pyftdi` (real transport) · borrow
**udsoncan** connection abstraction + service/DTC modelling · study
**KWP2000-CAN** + **ecu-diagnostics** for KWP2000-over-K-line layering · own
GEMS service layer + virtual ECU on top.

## The timing problem (hardest part, why generic adapters fail)

**(a) 5-baud slow init needs bit-level line control.** ISO 9141/KWP2000
slow-init sends a 7-bit address at 5 bit/s = 200 ms/bit. No UART supports 5 baud
— must **bit-bang** TX (pyftdi bit-bang mode), then switch to 10.4 kbit/s to
read the 0x55 sync byte + keybytes. Fast init (single 25 ms low / 25 ms high
pulse) is easier but still sub-UART timing.

**(b) FTDI latency timer WILL destroy inter-byte timing at default.** FTDI
buffers RX up to 16 ms before forwarding. KWP2000 timing (P1 inter-byte 0–20ms;
P2 req→resp 25–50ms; P3 inter-message ~55ms; P4 5–20ms) gets smeared. **Fix:
set latency timer to 1 ms** — non-negotiable, belongs in transport `open()`.

**(c) Echo / garbage bytes.** K-line is single-wire half-duplex → every TX byte
is echoed to RX (read and discard own echo). FTDI bit-bang leaves FIFO junk;
drain up to ~256 bytes after mode switch. Transport must handle echo-cancel +
buffer draining.

**Consequences:** Prefer a **smart adapter** (STN/OBDLink or Arduino/ESP32/
Macchina running init+framing in firmware) so Python does no sub-ms timing —
BUT support both dumb-FTDI and smart-adapter behind one interface. Isolate ALL
timing in the transport layer; dedicated I/O thread or asyncio feeding decoded
frames via queue.

## Proposed package layout

```
gems_t4/
├─ transport/          # ONLY timing-aware code
│  ├─ base.py          # Transport ABC (udsoncan-BaseConnection shaped)
│  ├─ kline_ftdi.py    # pyftdi bit-bang init + pyserial 10.4k, echo cancel, latency=1ms
│  ├─ kline_smart_adapter.py  # STN/Arduino firmware does init; simple line protocol
│  ├─ virtual.py       # in-process link to VirtualEcu (no timing)
│  └─ vcsi_chain.py    # models laptop→VCSI→J1962 link states
├─ protocol/           # KWP2000/ISO-14230 framing & init — pure, no I/O sleeps
│  ├─ framing.py       # header/format byte, length, checksum
│  ├─ init.py          # slow_init(addr) / fast_init(); keybyte negotiation
│  ├─ timing.py        # P1–P4 constants + timing policy
│  ├─ session.py       # diagnostic session ($10), tester-present ($3E)
│  ├─ security.py      # seed/key security access ($27) for programming
│  └─ services.py      # SID request/response + NegativeResponse ($7F)
├─ gems/               # GEMS-specific meaning on KWP services
│  ├─ ecu_profile.py   # K-line address, keybytes, which SIDs/records exist
│  ├─ dtc.py           # read/clear DTCs → GEMS fault table
│  ├─ livedata.py      # $61 record IDs → decoded measures + units + bandwidth
│  ├─ actuators.py     # actuator drives + refusal interlocks
│  ├─ programming.py   # read/write memory, ZCS/VIN/immobiliser coding, flash
│  └─ scenarios.py     # healthy / coolant-fail / cyl-3 misfire / lambda-heater
├─ app/                # presentation — CLI now, Win98 UI later (same stack)
│  ├─ cli.py           # Typer/Click
│  ├─ session_service.py
│  └─ render.py        # Rich tables/gauges; "Communicating with ECU…" waits
├─ config/             # ecu_profiles/*.yaml, fault tables, $61 record maps
└─ tests/ {unit, integration, hardware}
```

Load-bearing seam: `KwpClient(transport, timing)` takes ANY `Transport` (real
K-line or `VirtualTransport`), so the whole protocol/gems/app stack is exercised
identically on bench or against the fake ECU (udsoncan Client-wraps-Connection
pattern applied to KWP2000).

## Virtual ECU (develop/test without a car)

- **`VirtualEcu`** — state machine + data model, knows nothing about serial.
  Holds engine state (RPM, coolant warm-up curve, idle hunt, battery), DTC set,
  active fault scenario, session + security-lock state. One method:
  `handle(request) -> Response`. Answers $61 records, returns DTCs, honours
  session/security transitions, executes/refuses actuators, returns $7F for
  unsupported IDs — exactly T4 behaviour.
- **`VirtualTransport(Transport)`** — calls `VirtualEcu.handle()` in-process.
  Injects configurable latency + "Communicating with ECU…" delays (the
  "waiting" pillar) and simulates link failures (VCSI unplugged).
- **`Scenario`** drives DTCs + live-data perturbation + actuator outcomes from
  one object → coherent symptoms across every screen.

## Programming safety (gate every write)

1. Read-before-write / mandatory checksum-verified **backup** to disk (VIN, ECU
   id, timestamp, tool version).
2. **Verify-after-write** read-back byte-compare; default verify=True.
3. **Checksum discipline** — validate before offering write, recompute after
   modifying calibration; bad checksum is a common brick cause.
4. **Session + security gating** — writes require correct session ($10) + passed
   security access ($27). Mirror the ECU's own $7F refusals.
5. **Precondition interlocks** — refuse flash with engine running / low battery /
   unstable K-line (doubles as characterful refusal + genuine safety gate).
6. **Dry-run + explicit typed confirmation.**
7. **Separate coding (small reversible ZCS/VIN/immobiliser writes) from full
   calibration flash** — coding ships earlier, lower risk.

## Phased build plan

1. Skeleton + contracts (no hardware): Transport ABC, Request/Response,
   KwpClient, VirtualEcu + VirtualTransport, healthy scenario. `python -m gems_t4 live
   --fake` works.
2. Protocol depth on fake: full $61 map, DTC read/clear, session/tester-present,
   actuators with interlocks, all 4 fault scenarios, bandwidth model, full
   integration suite.
3. Real transport — smart adapter first (firmware does init, lowest risk),
   contract suite vs bench ECU, capture real traces as fixtures.
4. Real transport — dumb FTDI: pyftdi bit-bang slow init, latency=1ms, echo
   cancel, buffer drain. Validate vs same bench ECU + traces.
5. Programming, gated: coding first (ZCS/VIN/immobiliser), then calibration read
   + backup, full flash last behind all interlocks, on a sacrificial bench ECU.
6. CLI polish → UI reuses same KwpClient/services.

Related: [[research-kline-protocols]], [[research-gems-hardware]],
[[research-opensource-tools]], [[research-hardware-interfaces]],
[[research-gems-data]], [[gems-p38-focus]]
