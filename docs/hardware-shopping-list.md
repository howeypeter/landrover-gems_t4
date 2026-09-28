# Hardware shopping / build list — two-board K-line rig

Consolidated parts list for the current design (2026-09-27). Companion to the
pin-exact architecture in [`two-board-rig.md`](two-board-rig.md), the protection
detail in [`adapter-hardware-improvements.md`](adapter-hardware-improvements.md),
and the 10AS wiring in [`10as-pinout.md`](10as-pinout.md). The older JLCPCB
package (`hardware/gems-2pcb/`) still owns fab/BOM mechanics.

Two build tiers:
- **GEMS-simple** — everything needed to talk to the GEMS ECU (bench + car).
- **Universal** — adds the one net that makes Board 1 a general pre-CAN K-line
  adapter (the external L-line driver). See `two-board-rig.md` → "Multi-vehicle
  scope".

> **Inventory note:** there is **one** Pico and it works. No board was ever
> destroyed (the 2026-09-16 "dead Pico" was a misplaced injection wire — see the
> near-miss note in `adapter-hardware-improvements.md`). So no forced replacement;
> a spare is optional convenience only.

---

## 1 · Board 1 — MAIN (universal adapter)

| Item | Spec | Have? | Notes |
|---|---|---|---|
| Raspberry Pi Pico / Pico 2 (W) | RP2040/RP2350 | ✅ have (1) | 2 hardware UARTs → drives both transceivers |
| ST L9637D ×**2** (U1 + U3) | SO-8 + SO-8→DIP breakout ×2 | have 2 chips | **U1** = engine K-line (UART0 GP0/1); **U3** = 2nd channel (UART1 GP4/5) for 10AS/EAS/SRS |
| Resistor 510 Ω ×**2** (R1, R2) | ¼ W | — | **required** K→Vs pull-up, one per transceiver |
| **TVS 1.5KE24A** | 1500 W, 24 V, unidirectional | ✅ have (20-pk) | 12 V-node clamp (protects both Vs + the buck). DO-27 leads are fat: ream/bend |
| Inline fuse + holder | **1–2 A** | — | one, on the +12 V (OBD pin 16) feed; covers both chips + buck |
| **Buck converter 12→5 V** | fixed 5 V, 5–30 Vin, 3 A | ✅ have (6-pk) | OBD-12V → Pico 5 V so it's self-powered on-car (route A) |
| **Schottky 1N5817** | 1 A, 20 V | ✅ have (pk) | buck 5 V → **VSYS (pin 39)**; diode-ORs with USB, no switch. Band toward Pico |
| (opt.) Zener/TVS ~5.6–6.2 V | e.g. SMAJ5.0A | — | VSYS→GND, failsafe vs a shorted buck |
| Cap 100 nF ceramic ("104") | 50 V+ | — | optional Vcc decoupling. **Skip** the ≤1.3 nF K cap |
| **male J1962 pigtail** | OBD2 plug on a flying lead | — | into a car OR into Board 2 |
| PCB screw terminal blocks | 5 mm pitch, several | — | full 16-pin pigtail lands here; **two K-patch banks** (A→U1, B→U3) |

### Enclosure (Board 1 box)
Only **two things enter the box**: the **OBD2 pigtail** and the **microUSB**.
Everything else is internal. Notes:
- **Plastic / non-metallic box** — the Pico 2 W has a PCB antenna; metal kills
  WiFi/BLE.
- **USB to the wall:** a **panel-mount USB extension** to a box-wall connector is
  cleaner and saves the Pico's fragile onboard micro-USB (vs. a bare cutout).
- **JP1 access:** if you'll switch car-OBD ↔ GEMS/0xDA modes often, bring JP1 out
  as a **panel toggle**; otherwise leave it an internal jumper.
- **Optional status LED** on the face (power/comms).

### Universal build — add for the external L-line driver (multi-make)
The L9637D senses but can't **drive** L; 5-baud-init cars (VAG KWP1281 etc.) need L driven.

| Item | Spec | Notes |
|---|---|---|
| NPN transistor or N-MOSFET | ≥40 V, small-signal (e.g. 2N7002 / BC337) | open-collector L driver |
| Resistor ~1 kΩ | ¼ W | GPIO → base/gate |
| Resistor ~510 Ω–1 kΩ | ¼ W | L-bus pull-up |
| (1 Pico GPIO) | — | firmware "drive L" line |

GEMS-simple build omits all four (LI→GND, LO→n/c, passive JP1 strap only).

---

## 2 · Board 2 — BENCH hub

| Item | Spec | Notes |
|---|---|---|
| **female J1962 pigtail** | OBD2 socket on a flying lead | receives Board 1 |
| PCB screw terminal blocks | 5 mm pitch, several | one for the OBD pigtail, one → ECU, one → 10AS |
| DC barrel jack | 2.1 mm (or 2-pos terminal) | bench 12 V in |
| Schottky diode | SS54 / 1N5822 (≥3–5 A) | reverse-polarity protect on the DC input |
| Fuse + holder | **2 A** | main bench fuse |
| Toggle switch (PWR) | SPST, 12 V ≥5 A | master 12 V |
| Toggle switch (IGN) | SPST, 12 V ≥3 A | ECU ignition feed (C1033 p8) |

---

## 3 · Connections & build materials

| Item | Spec | Notes |
|---|---|---|
| Perfboard | 0.1″ pitch, ×2 | one per board |
| Hookup wire | 22 AWG | keep +12 V / ECU-power runs good for a few A |
| Dupont / header pins | assorted | bench wiring |
| USB cable | data-capable micro/USB-C | Pico power + data (USB-only power — no buck/Schottky/VSYS) |

---

## 4 · 10AS branch (immobiliser / EKA path)

| Item | Spec | Have? | Notes |
|---|---|---|---|
| Lucas 10AS unit | AMR 6428, NAS 315 MHz | ✅ have | bench unit |
| C225 / C274 mating connectors or pigtails | grey 26-way / green 12-way | — | onto Board 2's 10AS terminal block |
| Momentary pushbutton | any | — | simulates the door key switch (C225 pin 8) if testing EKA |

Off-board wire: **10AS C225 pin 15 → ECU C1017 pin 26** (coded mobilise). See
`10as-pinout.md`.

---

## 5 · Chip reading (EPROM / EEPROM)

| Item | Spec | Have? | Notes |
|---|---|---|---|
| XGecu T48 programmer | "+3 parts" bundle | ✅ bought (~arriving) | reads 27C512 / 27C1001 / 28C16 |
| SOIC-8 test clip | ~$8 | — | in-circuit reads of the 10AS EEPROM (SOIC-8) |
| W27C512 / W27C010 | reusable EEPROM equivalents | — | **only if** pursuing the immo-delete chip-patch write-path (speculative) |

---

## 6 · Do NOT buy (per decisions)

- ✅ **Buck + 1N5817 → VSYS is now IN the build** (route A, decided 2026-09-28) —
  OBD-12V powers the Pico on-car; USB optional. (Was "USB-only"; reversed.)
- ❌ **GPIO injection clamp diodes + 1 kΩ leads** — GPIO sensor injection retired;
  any residual sensor-ID work uses an **isolated 0–5 V supply + K-line observe**
  (`bench/live_diff.py`), not the Pico's pins.
- ❌ **≤1.3 nF K-line cap** — optional EMI nicety, skip.
- ❌ **CAN / J1850 hardware** — out of scope; the L9637D is K-line only.
- ❌ **Nanocom / Hawkeye** — would read the EKA directly, defeating the RE goal.

---

## 7 · Immediate buy / on-hand (dual-transceiver, on-car-powered Board 1)

**On hand already:** Pico, **2× L9637D**, **1.5KE24A** TVS (20-pk), **buck**
(6-pk), **1N5817** (pk).

**Still to get:**
- **2× SO-8→DIP breakout** (one per L9637D)
- **2× 510 Ω** resistor (R1, R2 — one pull-up per transceiver)
- **1–2 A inline fuse** + holder (one, covers both chips + buck)
- **male + female J1962 pigtail** pair
- **PCB-mount screw terminal blocks** (5 mm pitch, several — full 16-pin + 2 K-patch banks)
- Board 2: **DC barrel jack**, **2 A fuse**, two **toggle switches**
- **2× perfboard**, 22 AWG wire
- (opt.) **~5.6–6.2 V Zener/TVS** for the VSYS failsafe

Add later for **universal**: the L-driver transistor + 2 resistors. Add for
**10AS work**: C225/C274 pigtails + a momentary button. Add for **chip reads**:
the SOIC-8 clip (T48 already bought).
