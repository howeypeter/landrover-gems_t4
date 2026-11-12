# Board 1 (Dual K-Line) — handoff for Flux.ai

Snapshot date: 2026-10-20. KiCad project: `hardware/PCB_Board1_Simplified/PCB_Board1_Dual_Kline.kicad_pcb` (plus `.kicad_sch`). Backup of the state before the current routing pass: `hardware/PCB_Board1_Simplified_backup_2026-10-20_1017/`.

## Purpose

Two K-line channels, each with a read/write K node and a read-only listen (LI) tap, driven by a Pico 2 W. Channel 1 is U2 (J4 terminals), channel 2 is U3 (J5 terminals). Power comes from a 12 V OBD input, through a switch, to a 5 V buck feeding the Pico's VSYS.

## Board

- Outline: 85 x 75 mm. Edge.Cuts corners at (56.025, 72.905) and (141.025, 147.905) mm.
- 2 copper layers. B.Cu is a GND pour (`GND_bottom_pour`, 0.5 mm inset).
- Title on F.Silkscreen at the bottom edge: `MAIN BOARD — 2 K/L-LINE CHANNELS (R/W) · 2 LISTEN (RO)`.

## Power chain (as built)

```
J1 (12V IN, OBD-16 top pin / GND OBD-5 bottom pin)
  -> F1 (1A fuse)
  -> F1 pin 2 = /12V_F -> D1 anode (1N5817 reverse-polarity)
  -> D1 cathode = /SW_IN -> J3 pin 1 (4-position ignition switch)
  -> J3 pins 2 and 3 = /12V_SW (bridged on the board)
  -> /12V_SW feeds U2 pin 7, U3 pin 7, U4 pin 1 (buck IN), D2 TVS, R1 pin 2, R2 pin 2
  -> U4 (AKEYSRC 5 V 3 A buck module): pin 1 +IN, pin 2 GND IN, pin 3 GND OUT, pin 4 +OUT (5V)
  -> D3 (1N5817 VSYS feed) -> Pico pin 39 (VSYS)
```

D2 = 1.5KE24A TVS on /12V_SW. J1 is a 2-position terminal (pin 1 = 12 V, pin 2 = GND).

## Parts and placement (mm, footprint origins)

| Ref | Part | Position / note |
|---|---|---|
| U1 | Raspberry Pi Pico 2 W | (123.19, 100.33), rot 0. Pin 1 at (113.5, 76.2), pin 3 = GND, pin 36 = 3V3 at (132.88, 86.36), pin 39 = VSYS |
| U2 | L9637D (SOIC-8), channel 1 | (79.68, 112.31), rot 90 |
| U3 | L9637D (SOIC-8), channel 2 | (79.68, 133.31), rot -90 (rotated 180° from original) |
| U4 | AKEYSRC buck module (12.3 x 17.6 mm) | (93.78, 101.51) |
| J1 | 2-pos screw terminal, 12 V / GND | (62.5, 83.82), rot -90 |
| J3 | 4-pos switch terminal | top, pins at y = 77.9 mm, x = 96.52 / 99.06 / 101.6 / 104.14 |
| J4 | 3-pos terminal, channel 1 (K1, K1, LI1) | (62, 109.5), rot -90. Top pin 1 K1, middle pin 2 K1, bottom pin 3 LI1 — labels `U2 RW`, `U2 RW`, `U2 RO` from top |
| J5 | 3-pos terminal, channel 2 (K2, K2, LI2) | (62, 123.5), rot -90. Labels `U3 RW`, `U3 RW`, `U3 RO` from top |
| F1 | 1 A fuse holder | (76.5, 76.5) area; pads at (71.24, 79.0) = 12V_IN, (86.24, 79.0) = 12V_F. Footprint: `Board1_Custom:Fuseholder_2pin_5x20` |
| D1 | 1N5817 reverse-polarity | pads (83.82, 88.9) anode/12V_F, (93.98, 88.9) cathode/SW_IN |
| D2 | 1.5KE24A TVS | pads (71.5, 89.65) = 12V_SW, (71.5, 102.35) = GND |
| D3 | 1N5817 VSYS feed | pads (91.44, 116.84) 5V, (91.44, 127.0) VSYS |
| R1 | 510 Ω 1 W K1 pull-up | (63.0, 106.0), rot 90. Pad 1 K1 at (63.0, 106.0), pad 2 12V_SW at (63.0, 95.84) |
| R2 | 510 Ω 1 W K2 pull-up | (74.5, 136.0), rot -90. Pad 1 K2 at (74.5, 136.0), pad 2 12V_SW at (74.5, 146.16) |
| C1 | 100 nF decoupling, channel 1 | pads (81.68, 120.31) GND, (86.68, 120.31) 3V3 |
| C2 | 100 nF decoupling, channel 2 | pads (86.36, 127.0) 3V3, (81.36, 127.0) GND |
| TP1–TP8 | test pads | along the bottom edge (y ≈ 71 mm at the original layout; to be placed after routing) |

Notes on the rotation convention: KiCad writes -90 for 270° rotation.

## Net mapping

- **Channel 1 (U2):** pin 1 RX1, pin 2 LO1, pin 3 3V3, pin 4 TX1, pin 5 GND, pin 6 K1, pin 7 12V_SW, pin 8 LI1
- **Channel 2 (U3, rotated):** pin 1 RX2, pin 2 LO2, pin 3 3V3, pin 4 TX2, pin 5 GND, pin 6 K2, pin 7 12V_SW, pin 8 LI2
- **J4:** pin 1 K1, pin 2 K1, pin 3 LI1 (LI1 is the read-only tap)
- **J5:** pin 1 K2, pin 2 K2, pin 3 LI2
- **Pico left column (x = 113.5 mm):** pin 1 TX1 (76.2), pin 2 RX1 (78.74), pin 4 LO1 (83.82), pin 6 TX2 (88.9), pin 7 RX2 (91.44), pin 9 LO2 (96.52)
- **Pico right column:** pin 36 3V3 (132.88, 86.36), pin 39 VSYS (132.88, 78.74)

## Silkscreen

Terminal labels (done): `+12V (OBD-16)` above J1's 12 V pin, `GND (OBD-5)` below its GND pin. K-line labels as above. Chip labels `L9637D` under U2 and U3, with a pin 1 dot on each. Part labels for the fuse, diodes, buck, Pico pins and power nets are placed in the file. Two earlier labels were removed to make room: `K2 PU` and C1's `3V3 DEC`. TVS 24V was removed when R1 moved.

## Routing status (F.Cu = front, B.Cu = back; widths 0.25 mm for signals, 0.8 mm for 12 V)

Routed:
- 12V_IN: J1 12 V pin to F1 pin 1
- 12V_F: F1 pin 2 to D1 anode
- SW_IN: D1 cathode to J3 pin 1
- 12V_SW: J3 pins 2 and 3 bridged. The rest of the net is open.
- 3V3: U3 pin 3 to C1 and C2 3V3 pads (via y = 124 mm); the Pico's pin 36 comes through the middle of the board on the back layer (vias at (134.2, 86.36) and at the x = 104.5 channel) to C1
- GND: U3 pin 5 via to the pour (77.8, 137.0). The back-layer pour supplies the other GND pads.
- K2: R2 pin 1 to U3 pin 6 (passes under pin 5)
- 12V_SW: R2 pin 2 to U3 pin 7 (under the K2 run)
- TX1: U2 pin 4 via (81.6, 116.0), back-layer run to the Pico's pin 1 via (111.7, 76.2)
- RX1: U2 pin 1 via (77.8, 116.0), back-layer to x = 74, front/back hops along y = 81.5 mm, to the Pico's pin 2 at (113.5, 78.74)
- LO1: U2 pin 2 via (79.0, 117.0), back-layer west leg at x = 69.5, hops along y = 80.5 mm, to the Pico's pin 4 via (111.7, 83.82)
- RX2: Pico pin 7 F run along y = 91.44 mm, x = 102.5 mm down, back-layer y = 122.5 mm, to U3 pin 1 via (84.0, 130.8)

Still open (16 unconnected pads, per the latest DRC):
- K1: J4 pads 1 and 2, R1 pin 1, U2 pin 6
- K2: J5 pads 1 and 2 (R2 pin 1 is routed to U3)
- LI1: J4 pad 3 to U2 pin 8
- LI2: J5 pad 3 to U3 pin 8
- TX2: U3 pin 4 to Pico pin 6
- LO2: U3 pin 2 to Pico pin 9
- 12V_SW: R1 pin 2, D2 pin 1, U2 pin 7 and U4 pin 1 (R2 pin 2 is routed to U3 pin 7)
- 5V: U4 pin 4 to D3 pin 2
- VSYS: D3 pin 1 to Pico pin 39

## DRC status (last run 2026-10-20 14:27)

- 2 errors: RF keep-out on the Pico's F.Paste pads (expected; the module's own paste pads sit in its copper keep-out).
- 16 unconnected pads, all in the open list above.
- 0 footprint errors. 0 silkscreen warnings.
- Known: U3's copy in the board no longer matches its library footprint after the rotation. Use Update Footprint from Library on U3 and confirm it stays at -90.

## Known problems and decisions

- **Pico clearances:** the Pico's copper keep-out (RF) covers the Pico's right edge at about x ≥ 136 mm on both layers, so the 3V3 run passes under the module (back layer) instead.
- **Back-layer crossings:** every crossing between the TX1 back run (x = 88 mm, y 76–116 mm), the 3V3 back run (x = 104.5 mm, y 86–120 mm; y = 86.36 mm, x 104.5–134 mm) and the RX2 back run (y = 122.5 mm) needs a via hop. Several are in place.
- **Through-hole parts:** R1, R2, C1, C2, D1, D2, D3, F1 and the terminals are through-hole. A back-layer track that touches one of their pads will short. Keep the back layer clear of those holes; keep the solder-mask bridge clearance (≥ 0.5 mm) from D2's pads.
- **Label text:** where a silk label touches a pad or a reference, the DRC flags it. Keep labels off pads.

## Workflow notes

- KiCad writes coordinates without trailing zeros. When editing the board file directly, match numbers by value, not by text.
- Always revert the PCB in KiCad after editing the file on disk, before saving from KiCad. Otherwise the open copy overwrites the edits.
- Backups: copy the `hardware/PCB_Board1_Simplified` folder to a dated sibling before big changes.

## Open decisions

- TVS 24V label: no room beside D2 yet. Re-add it once the routing is in.
- Test pads TP1–TP8: place after routing, on nets worth probing (3V3, 5V, 12V_SW, GND, K1, K2, TX/RX).
- Whether to keep J1's 12 V and GND pin labels as they are: yes, as placed.
