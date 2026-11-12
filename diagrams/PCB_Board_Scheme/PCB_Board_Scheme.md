# Board 1 — Electrical Design

Full electrical design for Board 1 (the universal K-line adapter): components,
pins, and nets. This is a **schematic-level reference, not a PCB layout** — no
placement, routing, or layer guidance here (see `docs/two-board-rig.md` for that).

Companion docs: `docs/two-board-rig.md` (full narrative + design rationale),
`docs/hardware-shopping-list.md` (parts to buy), `docs/dlc-pinouts.md` (which
OBD pin reaches which vehicle module).

---

## 1. Bill of materials

| Ref | Part | Value / Spec | Notes |
|---|---|---|---|
| J1 | OBD2 pigtail | Male J1962, 9 wires terminated | Wires land directly on the board's terminal block — no separate connector |
| U1 | Raspberry Pi Pico 2 W | — | Host MCU; two hardware UARTs drive U2 and U3 independently |
| U2 | ST L9637D | SOIC-8 | K-line transceiver, primary channel (engine) |
| U3 | ST L9637D | SOIC-8 | K-line transceiver, secondary channel |
| R1 | Resistor | 510 Ω, **1 W** | K-line pull-up for U2 (K ↔ Vs). K held low dissipates ~0.28 W at 12 V, ~0.41 W at 14.4 V, ~0.64 W at 18 V — ¼ W has no margin |
| R2 | Resistor | 510 Ω, **1 W** | K-line pull-up for U3 (K ↔ Vs), same rating and rationale as R1 |
| F1 | Fuse | 1 A | Inline on the +12 V input, protects the whole board |
| D1 | TVS diode | 1.5KE24A, unidirectional, 10/1000 µs. VRWM = 20.5 V, VBR = 22.8–25.2 V, VC(max) = 33.2 V ("24" is the breakdown-grade name, not the standoff voltage) | Clamps the fused 12 V node |
| Q1 | P-channel MOSFET | Automotive-rated, VDS ≥ −40 V, low RDS(on) — exact MPN TBD | Reverse-polarity protection ahead of REG1 (ideal-diode topology): source → VS_FUSED, drain → VIN_PROT |
| R3 | Resistor | ~10 kΩ | Q1 gate → GND — biases Q1 on for correct polarity, off for reversed polarity |
| REG1 | Buck converter | **LMR51610-Q1** (TI, automotive, 65 V/1 A sync buck, SOT-23), fixed 5 V out | Steps 12 V down for the Pico. ~2× input-voltage margin over D1's 33.2 V clamp |
| D2 | Schottky diode | 1N5817, 1 A / 20 V | Buck output → Pico VSYS; diode-ORs with USB power |
| C1 | Ceramic capacitor | 100 nF ("104"), 50 V+ | Vcc decoupling for U2, mounted close to U2 pin 3 |
| C2 | Ceramic capacitor | 100 nF ("104"), 50 V+ | Vcc decoupling for U3, mounted close to U3 pin 3 |

---

## 2. J1 — OBD pigtail terminal assignment

**The terminal block IS the pigtail termination — there is no separate patch
layer.** Each pigtail wire lands directly on one of these 9 terminals; the
terminals are screw-type, so reconfiguring which vehicle line feeds which
transceiver channel means physically moving a wire to a different terminal.

Physical order, left to right, single row:

```
[ A1 ][ A2 ][ A3 ]   [ B1 ][ B2 ][ B3 ]   [ 12V ]   [ GND ][ GND ]
```

**Board silkscreen uses friendlier names for the same six terminals:**
`K1-A`=A1, `K1-B`=A2, `K1-RO`=A3, `K2-A`=B1, `K2-B`=B2, `K2-RO`=B3. Both names
refer to the identical physical screw terminal; this doc keeps the A/B lettering
for brevity, the board itself prints the K1/K2 names.

**Full 6-terminal assignment FINALIZED (2026-10-20):**

| Terminal | Internal net | This build's OBD pin / tap |
|---|---|---|
| A1 (`K1-A`) | K1 (U2 pin 6) | pin 7 — engine K-line |
| A2 (`K1-B`) | K1 (U2 pin 6) — **same node as A1** | pin 15 — L-line, **intentionally tied to A1** (keeps the GEMS 0xDA L↔K strap permanently open) |
| A3 (`K1-RO`) | LI1 (U2 pin 8, read-only) | pin 13 — **SRS/airbag diagnostic line** (RAVE-verified, `docs/dlc-pinouts.md`). **Passive listen tap only** — LI cannot drive, so this board can never write to the airbag bus, only sniff it. No active SRS diagnostics (that would need a bidirectional channel, which isn't spare). |
| B1 (`K2-A`) | K2 (U3 pin 6) | pin 8 — **10AS diagnostic bus**. Bidirectional — this channel both writes (init/request frames) and reads, needed for any real 10AS exchange (e.g. the EKA read goal); the 10AS protocol itself is still unmapped, but the transport already supports raw writes via `select_channel(1)` + `raw_xfer()`. |
| B2 (`K2-B`) | K2 (U3 pin 6) — same node as B1 | spare slot on the K2/10AS node — not currently used |
| B3 (`K2-RO`) | LI2 (U3 pin 8, read-only) | **10AS→ECM mobilise line** (C225 pin 15 → C1017 pin 26) — **not on the OBD2 pigtail at all**; tapped via a separate direct splice onto that wire at the bench. Passive listen tap only. Per the 2026-09-28 PIO+DMA capture, this line is DC-enable-like with no decodable serial data, so the simple LI comparator read (`read_pins()`/`monitor_l()`) is sufficient — no need for the dedicated high-speed sniffer for routine monitoring. **Verify the line's voltage swing against the L9637D's comparator threshold before relying on this** — not yet explicitly checked. |
| 12V | 12V_IN | pin 16 — battery +12 V |
| GND | GND | **not landed** — pin 4 (chassis ground) deliberately left unconnected, see §6 |
| GND | GND | pin 5 — signal ground (Board 1's only ground reference) |

Other OBD pins (1, 2, 3, 6, 9, 10, 11, 12, 14 — including CAN on 6/14 and
J1850 on 2/10) are **not landed on any terminal** in this build.

**Why this split (K1 active, K2 active, both RO passive-only):** there are
exactly 2 bidirectional channels (K1, K2) and at this point 3 candidate jobs —
(1) engine K+L tied for 0xDA, (2) 10AS diagnostics on pin 8, (3) true independent
read access to SRS and the immobiliser mobilise line. Only 2 of those can be
*active/bidirectional* at once; SRS and the mobilise line don't need write
access for their purpose here (sniffing state, not driving it — and for the
mobilise line especially, read-only is also a deliberate safety property, not
just a resource constraint), so parking both on the RO pins is the right fit
rather than a compromise.

---

## 3. U2 — L9637D (primary / engine channel)

| Pin | Name | Net | Direction |
|---|---|---|---|
| 1 | RX | K1_RX → Pico GP1 | chip output (K state → Pico) |
| 2 | LO | K1_LO → Pico GP2 | chip output (L-comparator result → Pico) |
| 3 | VCC | P3V3 | power in (from Pico 3V3) |
| 4 | TX | K1_TX ← Pico GP0 | chip input (Pico drives K) |
| 5 | GND | GND | power in |
| 6 | K | K1 (= terminal A1/A2) | bidirectional bus |
| 7 | Vs | VS_FUSED | power in (fused/TVS'd 12 V) |
| 8 | LI | LI1 (= terminal A3) | input, read-only listen tap |

**R1 (510 Ω)** bridges pin 6 (K) and pin 7 (Vs) — the required K-line pull-up.
**C1 (100 nF)** bridges pin 3 (VCC) and pin 5 (GND) — Vcc decoupling, mounted
close to the chip.

---

## 4. U3 — L9637D (secondary channel)

Identical pin function to U2, on its own independent net set:

| Pin | Name | Net | Direction |
|---|---|---|---|
| 1 | RX | K2_RX → Pico GP5 | chip output |
| 2 | LO | K2_LO → Pico GP6 | chip output |
| 3 | VCC | P3V3 | power in |
| 4 | TX | K2_TX ← Pico GP4 | chip input |
| 5 | GND | GND | power in |
| 6 | K | K2 (= terminal B1/B2) | bidirectional bus |
| 7 | Vs | VS_FUSED | power in |
| 8 | LI | LI2 (= terminal B3) | input, read-only listen tap |

**R2 (510 Ω)** bridges pin 6 (K) and pin 7 (Vs) — the pull-up for the secondary
channel. **C2 (100 nF)** bridges pin 3 (VCC) and pin 5 (GND) — Vcc decoupling,
mounted close to the chip.

⚠️ **K1 and K2 are separate nets — never bridge them.** Bridging the two K-line
buses recreates the shared-node contention that caused the earlier "phantom
echo" when probing the 10AS on the same node as the engine ECU.

---

## 5. Power path

```
J1 pin 16 (+12V)
   │
   ▼
  [F1] 1A fuse
   │
   ▼
 VS_FUSED ──────────────┬───────────────┬──────────────────────┐
   │                    │               │                      │
   ▼                    ▼               ▼                      ▼
 [D1] TVS           U2 pin 7 (Vs)   U3 pin 7 (Vs)          [Q1] P-FET
 K(cathode)=VS_FUSED                                    reverse-polarity
 A(anode)=GND, clamp                                    protection (ideal diode)
                                                                 │
                                                                 ▼
                                                            VIN_PROT
                                                                 │
                                                                 ▼
                                                        REG1 VIN (LMR51610-Q1)
                                                          (buck 12→5V)
                                                                 │
                                                                 ▼
                                                            REG1 VOUT (5V)
                                                                 │
                                                                 ▼
                                                          [D2] 1N5817
                                                          (band → Pico)
                                                                 │
                                                                 ▼
                                                        Pico (U1) VSYS (pin 39)
                                                                 ▲
                                                                 │
                                                    (diode-ORs automatically
                                                     with USB VBUS — no switch)
```

- **F1 (1 A)** is the only fuse on the board — it protects both L9637D pull-ups,
  the TVS, and the buck path, since all three tap the same fused node.
- **D1 (TVS)** sits across VS_FUSED → GND with its **cathode (banded end) on
  VS_FUSED and anode on GND** — this keeps it reverse-biased (inert) during
  normal operation and lets it clamp only on a positive overvoltage spike,
  protecting both transceivers' Vs pins and Q1/REG1's input. VC(max) = 33.2 V
  (10/1000 µs, per the exact 1.5KE24A spec — see BOM); REG1's 65 V absolute-max
  input rating clears this with ~2× margin.
- **Q1 (P-channel MOSFET)** is a series reverse-polarity protection stage ahead
  of REG1 only — the L9637Ds tolerate reverse-supply conditions directly and
  sit upstream of Q1 on VS_FUSED, but the buck module's reverse behavior is
  unverified, so Q1 protects it. Standard ideal-diode topology: source tied to
  VS_FUSED, drain feeds VIN_PROT (REG1's input), gate pulled to GND through R3.
  On correct polarity this biases Q1 on (low RDS(on) drop); on reversed supply
  Vgs flips and Q1 (plus its body diode orientation) blocks conduction. Covers
  the case a keyed OBD connector doesn't — a miswired reconfigurable terminal
  (e.g. +12V landed on a GND slot) or reversed bench/jump-start polarity.
- **REG1 (LMR51610-Q1)** steps the protected 12 V rail down to a fixed 5 V.
  Automotive-qualified, 65 V absolute-max input — comfortably clears D1's
  33.2 V clamp. Full support-circuit values (inductor, input/output caps) come
  from the TI datasheet at layout time.
- **D2 (Schottky)** is in series between the buck's output and Pico VSYS. Its
  job is NOT protection — it lets the buck's 5 V and the Pico's own USB-VBUS
  path coexist on VSYS without back-feeding each other (a diode-OR). **Feed
  VSYS (pin 39) — never VBUS (pin 40).**
- With both USB and the fused 12 V present, VSYS sits at whichever source is
  higher; the lower source's diode is simply reverse-biased. No switch is
  needed — this is a passive, automatic handoff.

---

## 6. Ground

**CORRECTED (2026-10-20) — pin 4 is NOT landed; Board 1 grounds through pin 5
only.** The earlier "bond 4+5" decision is reversed — see rationale below.

| Source | Connects to net |
|---|---|
| J1 pin 5 (signal ground) | GND |
| U2 pin 5 | GND |
| U3 pin 5 | GND |
| REG1 GND | GND |
| U1 (Pico) GND | GND |
| D1 (TVS) anode | GND |
| R3 (Q1 gate pull-down) | GND |
| C1 pin B | GND |
| C2 pin B | GND |

J1 pin 4 (chassis ground) is **deliberately left unconnected** — not landed on
either GND terminal.

**Why this changed:** pins 4 and 5 are electrically distinct on the real
vehicle (chassis-return vs. a dedicated clean reference for diagnostic gear),
and per RAVE (`docs/dlc-pinouts.md`) they go to **different splice points** on
this vehicle — pin 4 → S204/E201, pin 5 → E200 — so they are **not** already
bonded near the connector as earlier assumed. Board 1 is an external device;
bonding 4+5 on it would create a new current path between two ground networks
the OEM kept separate, letting chassis-ground noise/transients (starter crank,
alternator ripple) reach what's supposed to be the clean reference, through
thin signal-rated pigtail wiring never meant to carry chassis-ground current.
**Fix: use pin 5 only** — it's the pin J1962 provides specifically for this
purpose — and leave pin 4 off the board entirely, so Board 1 never bridges the
two ground networks and relies on the vehicle's own (OEM-designed) grounding
scheme for chassis duty. The second physical GND terminal slot stays wired to
the same internal GND net (it's one node, not two independent ones) but is
simply left unused unless a future need arises.

---

## 7. U1 (Pico 2 W) pin usage

| Pico pin | Net | Purpose |
|---|---|---|
| VSYS (39) | VSYS_5V | Power in from the buck (via D2), diode-OR'd with USB |
| VBUS (40) | — (not used) | USB power — never wired to anything on this board |
| 3V3 | P3V3 | Powers U2.VCC and U3.VCC |
| GND | GND | Common ground |
| GP0 | K1_TX | Drives U2's TX (K-line output) |
| GP1 | K1_RX | Reads U2's RX (K-line input) |
| GP2 | K1_LO | Reads U2's LI-comparator result (immobiliser-line sniffer, channel 1) |
| GP4 | K2_TX | Drives U3's TX |
| GP5 | K2_RX | Reads U3's RX |
| GP6 | K2_LO | Reads U3's LI-comparator result (channel 2) |

GP0/GP1 = UART0 (`Serial1`, driving U2). GP4/GP5 = UART1 (`Serial2`, driving
U3) — two independent hardware UARTs, so U2 and U3 can run at different bauds
simultaneously (e.g. engine at 10400, a 10AS-style bus at 9600).

⚠️ **Firmware note:** as of this writing, only the U2/Serial1 path is wired up
in `pico_kline_all`. Using U3 requires adding a `channel` selector (0 = Serial1,
1 = Serial2) to the host-protocol commands — the hardware is ready, the
firmware isn't yet.

---

## 8. Net summary (all nets, one place)

| Net | Members |
|---|---|
| K1 | Terminal A1, Terminal A2, U2 pin 6, R1 pin A |
| K1_TX | U2 pin 4, U1 GP0 |
| K1_RX | U2 pin 1, U1 GP1 |
| K1_LO | U2 pin 2, U1 GP2 |
| LI1 | Terminal A3 (`K1-RO`), U2 pin 8 — tapped to OBD pin 13 (SRS/airbag), passive listen only |
| K2 | Terminal B1, Terminal B2, U3 pin 6, R2 pin A |
| K2_TX | U3 pin 4, U1 GP4 |
| K2_RX | U3 pin 1, U1 GP5 |
| K2_LO | U3 pin 2, U1 GP6 |
| LI2 | Terminal B3 (`K2-RO`), U3 pin 8 — tapped to the 10AS→ECM mobilise line (off-OBD2 direct splice), passive listen only |
| 12V_IN | Terminal 12V, F1 pin A |
| VS_FUSED | F1 pin B, **D1 cathode**, U2 pin 7, U3 pin 7, Q1 source, R1 pin B, R2 pin B |
| VIN_PROT | Q1 drain, REG1 VIN |
| VSYS_5V | REG1 VOUT, D2 anode, D2 cathode → U1 VSYS |
| P3V3 | U1 3V3, U2 pin 3, U3 pin 3, C1 pin A, C2 pin A |
| GND | Terminal GND ×2 (only OBD pin 5 landed — pin 4 intentionally unconnected, see §6), U2 pin 5, U3 pin 5, REG1 GND, U1 GND, **D1 anode**, Q1 gate ← R3, C1 pin B, C2 pin B |

---

## 9. Design notes

- **Why A1/A2 are one node:** each channel's K-terminal is deliberately given
  two physical screw slots on the same net, so a second wire (like the L-line)
  can be landed alongside the primary K wire without extra hardware. For this
  GEMS build, that's used to permanently strap L (pin 15) to K on channel A,
  which is what opens the proprietary 0xDA diagnostic mode. To run plain OBD
  with no strap, unscrew the pin-15 wire from A2.
- **Why LI is a separate, unbussed net:** LI (pin 8) is the L9637D's read-only
  comparator input — it senses a line but can never drive it. Keeping it off
  the K node means you can tap it onto any signal you want to passively
  listen to without disturbing or loading whatever's on the K bus. **Finalized
  use (2026-10-20): LI1 (`K1-RO`) → SRS/airbag (OBD pin 13); LI2 (`K2-RO`) →
  the 10AS→ECM immobiliser mobilise line** (off-OBD2, direct splice). Both are
  safety-sensitive buses where read-only access isn't just convenient — it's a
  hardware guarantee this board can never accidentally write an actuation or
  state-change command onto either line.
- **Why two transceivers:** K1 and K2 are fully independent — different OBD
  pins, different pull-ups, different UARTs, different bauds. This lets the
  board hold two K-line sessions open at once (e.g. talking to the engine ECM
  while also reading a 10AS-style diagnostic bus), without the contention that
  comes from putting two vehicle modules on one shared node.
- **Why U1 = the Pico:** the Pico is the board's host/brain — it owns every
  protocol decision, both UARTs, and the wireless links — so it takes the
  U1 designator by convention; U2/U3 are the peripheral transceiver ICs it
  drives.
