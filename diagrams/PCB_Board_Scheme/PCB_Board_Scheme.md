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
| R1 | Resistor | 510 Ω | K-line pull-up for U2 (K ↔ Vs) |
| R2 | Resistor | 510 Ω | K-line pull-up for U3 (K ↔ Vs) |
| F1 | Fuse | 1 A | Inline on the +12 V input, protects the whole board |
| D1 | TVS diode | 1.5KE24A, 24 V standoff, unidirectional | Clamps the fused 12 V node |
| REG1 | Buck converter | Fixed 5 V out, 5–30 V in, 3 A | Steps 12 V down for the Pico |
| D2 | Schottky diode | 1N5817, 1 A / 20 V | Buck output → Pico VSYS; diode-ORs with USB power |

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

| Terminal | Internal net | This build's OBD pin |
|---|---|---|
| A1 | K1 (U2 pin 6) | pin 7 — engine K-line |
| A2 | K1 (U2 pin 6) — **same node as A1** | pin 15 — L-line, **intentionally tied to A1** (keeps the GEMS 0xDA L↔K strap permanently open) |
| A3 | LI1 (U2 pin 8, read-only) | not currently used |
| B1 | K2 (U3 pin 6) | pin 8 — 10AS diagnostic bus |
| B2 | K2 (U3 pin 6) — same node as B1 | not currently used |
| B3 | LI2 (U3 pin 8, read-only) | not currently used |
| 12V | 12V_IN | pin 16 — battery +12 V |
| GND | GND | pin 4 — chassis ground |
| GND | GND | pin 5 — signal ground |

Other OBD pins (1, 2, 3, 6, 9, 10, 11, 12, 13, 14 — including CAN on 6/14 and
J1850 on 2/10) are **not landed on any terminal** in this build.

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
channel.

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
 [D1] TVS           U2 pin 7 (Vs)   U3 pin 7 (Vs)          REG1 VIN
 1.5KE24A                                                  (buck 12→5V)
 (→ GND, clamp)                                                 │
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
  the TVS, and the buck, since all three tap the same fused node.
- **D1 (TVS)** sits across VS_FUSED → GND, clamping automotive load-dump spikes
  before they reach either transceiver's Vs pin or the buck's input.
- **REG1 (buck)** steps 12 V down to a fixed 5 V. Its input sees the same fused +
  TVS-protected node as the transceivers.
- **D2 (Schottky)** is in series between the buck's output and Pico VSYS. Its
  job is NOT protection — it lets the buck's 5 V and the Pico's own USB-VBUS
  path coexist on VSYS without back-feeding each other (a diode-OR). **Feed
  VSYS (pin 39) — never VBUS (pin 40).**
- With both USB and the fused 12 V present, VSYS sits at whichever source is
  higher; the lower source's diode is simply reverse-biased. No switch is
  needed — this is a passive, automatic handoff.

---

## 6. Ground

| Source | Connects to net |
|---|---|
| J1 pin 4 (chassis ground) | GND |
| J1 pin 5 (signal ground) | GND |
| U2 pin 5 | GND |
| U3 pin 5 | GND |
| REG1 GND | GND |
| U1 (Pico) GND | GND |
| D1 (TVS) cathode return | GND |

**Pins 4 and 5 are intentionally bonded into one net (GND).** They're
electrically distinct on a real vehicle (chassis vs. signal reference), but our
circuit is high-impedance/low-current (just reading/driving a K-line — no real
power switching), so the noise-isolation reason for keeping them separate
doesn't apply here. All grounds — both terminals, both transceivers, the buck,
and the Pico — are a single electrical net.

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
| LI1 | Terminal A3, U2 pin 8 |
| K2 | Terminal B1, Terminal B2, U3 pin 6, R2 pin A |
| K2_TX | U3 pin 4, U1 GP4 |
| K2_RX | U3 pin 1, U1 GP5 |
| K2_LO | U3 pin 2, U1 GP6 |
| LI2 | Terminal B3, U3 pin 8 |
| 12V_IN | Terminal 12V, F1 pin A |
| VS_FUSED | F1 pin B, D1 anode-side, U2 pin 7, U3 pin 7, REG1 VIN, R1 pin B, R2 pin B |
| VSYS_5V | REG1 VOUT, D2 anode, D2 cathode → U1 VSYS |
| P3V3 | U1 3V3, U2 pin 3, U3 pin 3 |
| GND | Terminal GND ×2 (OBD pins 4 & 5), U2 pin 5, U3 pin 5, REG1 GND, U1 GND, D1 cathode-side |

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
  listen to (e.g. the 10AS→ECM immobiliser mobilise line) without disturbing
  or loading whatever's on the K bus.
- **Why two transceivers:** K1 and K2 are fully independent — different OBD
  pins, different pull-ups, different UARTs, different bauds. This lets the
  board hold two K-line sessions open at once (e.g. talking to the engine ECM
  while also reading a 10AS-style diagnostic bus), without the contention that
  comes from putting two vehicle modules on one shared node.
- **Why U1 = the Pico:** the Pico is the board's host/brain — it owns every
  protocol decision, both UARTs, and the wireless links — so it takes the
  U1 designator by convention; U2/U3 are the peripheral transceiver ICs it
  drives.
