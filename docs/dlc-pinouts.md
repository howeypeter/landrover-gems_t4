# DLC (OBD-II / J1962) pinouts — VERIFIED from RAVE

Verified 2026-09-27 by reading the RAVE **DATA LINK CONNECTOR (D3)** circuit pages
directly, and cross-checking the connector pin numbering against pins whose J1962
meaning is fixed by the standard (so the pin numbers are real J1962 pins, not
assumed).

**Headline correction:** the project's earlier "single shared K-line on pin 7"
model is a **simplification and is wrong as stated.** These trucks use **multiple
separate diagnostic lines** on different DLC pins. The real dealer tool (T4) used a
**VCSI demultiplexer** precisely because there is more than one line to route to.

---

## Discovery 1 (NAS SFI-V8 / GEMS) — the user's vehicle

Source: `etlj970x.pdf`, section **D3 (DATA LINK CONNECTOR), pages 99–100**. DLC =
**X318**, harness connector **C2083**.

| DLC pin | Signal | Goes to | Wire |
|---:|---|---|---|
| 4 | Ground | S204/E201 | B |
| 5 | Ground | E200 | B |
| **7** | **K-line** | **Engine ECM (C1017 p23) + ABS ECU (C2084 p14)** — *shared* | WLG |
| **8** | **Diagnostic serial** | **Theft Alarm / 10AS** (Z163, C225 p17) | KB |
| **13** | **Diagnostic serial** | **Air Bag / SRS** (Z151, via C2097/C354) | — |
| **15** | **L-line** | Engine ECM (C1017 p20) + ABS ECU (C2084 p13) — *shared* | WK |
| 16 | +12 V battery | Satellite Fuse Box 2, F3 10 A | — |

**Three separate diagnostic lines on the Disco 1:**
1. **Pins 7 (K) + 15 (L)** — the "main" bus, **shared by Engine ECM + ABS**.
2. **Pin 8** — **10AS / theft alarm**, its **own** line.
3. **Pin 13** — **airbag / SRS**, its **own** line.

Consequences for this project:
- **Reaching the 10AS on a real Disco 1 requires DLC pin 8** — pin 7 never sees it.
- Our **bench** tied the 10AS onto the shared pin-7 K node (not how the car wires
  it) — consistent with the contention / "phantom echo" trouble.
- GEMS wakes on **K (pin 7)** alone; the L-line (pin 15) matters only for the 0xDA
  strap. See `two-board-rig.md`.

## P38 Range Rover (GEMS era, MY97) — for multi-model support (NOT the user's truck)

Source: `~/Downloads/rave/rave/pdf/lp/etlp970e.pdf` (model code **lp** = Range
Rover P38A), section **D3, pages 112–114**. DLC = **X318**, harness connector
**C231**. (The P38 has a **BeCM**; the Disco 1 does **not** — it has the 10AS.)

| DLC pin | Signal | Goes to | Wire |
|---:|---|---|---|
| 1 | Air-suspension delay-turn-off timer | Z260 | SR |
| 4, 5 | Ground | E252 | B/BP |
| **7** | **K-line** (shared) | **Engine ECM (C507 p23) + ABS + HEVAC + BeCM** | KR |
| **11, 12** | Air-suspension ECU | Z165 | WLG/WK |
| **13, 14** | Air Bag / SRS | Z151 | YK/YG/YLG |
| **15** | **L-line** (shared) | BeCM + HEVAC + ABS (not the petrol ECM) | LGR |
| 16 | +12 V battery | Fuse F33 | N |

**Key P38 difference — the BeCM is NOT on its own pin.** Verified directly:
BeCM (Z238) **C255 p8 → C231 p7 (KR)** and **C255 p17 → C231 p15 (LGR)** — i.e. the
BeCM **shares the main K/L bus (pins 7/15)** with the engine, ABS and HEVAC. That
is the **opposite** of the Disco 1, where the security module (10AS) got its own
pin 8. So on a P38 you reach the BeCM on the **same pins as the engine** (address it
by its module address on the shared bus); no extra DLC pin needed.

P38 also puts **EAS air suspension on pins 11/12** (Z165) and a delay timer on pin 1
— more separate lines (the EAS is a settings-bearing subsystem; see the QA-A3
backlog item).

---

## How the pin numbering was verified (not assumed)

For each connector, pins whose J1962 meaning is fixed by the standard came out
correct, which proves the harness-connector pin numbers = physical J1962 pins:

| J1962 fixed pin | Expected | Disco 1 (C2083) | P38 (C231) |
|---|---|---|---|
| 16 | +12 V battery | ✅ (F3 feed) | ✅ (F33 feed) |
| 4 / 5 | grounds | ✅ | ✅ |
| 7 | K-line | ✅ (→ ECM p23) | ✅ (→ ECM p23) |
| 15 | L-line | ✅ (→ ECM p20) | ✅ |

Manufacturer-discretionary pins (1, 3, 8, 9, 11, 12, 13, 14) are where the OEM hangs
the extra module buses — Disco 1 uses **8** (10AS) and **13** (SRS); P38 uses **1**
(air-susp timer), **11/12** (EAS), **13/14** (SRS).

## Not reachable with the L9637D (K-line transceiver)
- **CAN** (pins 6/14) — different silicon; the L9637D can't do it.
- **J1850** PWM/VPW (pins 2/10) — different physical layer.

Both can be *exposed* as unpopulated terminals/pads for a future daughterboard, but
the L9637D-based tool is the **K-line family (ISO 9141-2 / KWP2000)** only.
