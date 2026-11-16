# Board 2 Rev 1.1 (design notes; NOT the fabbed version)

Written 2026-11-15. **Rev 1.0 is already at the fab and its docs are unchanged**: `docs/board2-bom.md`, `hardware/board2-bom.csv`, `hardware/board2-bom-mouser.csv`, `docs/board2-order-checklist.md`, `docs/board2-pcb2-summary.md`. This file and the `board2-v1.1-*` files describe Rev 1.1 only. Nothing for Rev 1.1 has been ordered or exported.

Rev 1.1 lives in the Cherry Blossom project "Board 2 bench hub (PCB2) v1.1" (a copy of the v1.0 project). The v1.0 project is separate and untouched.

## What changed from Rev 1.0

| Area | Rev 1.0 (fabbed) | Rev 1.1 |
|---|---|---|
| J6-J9 part | Harwin M20-9980546, vertical 2x5, tin | Harwin **M20-9740546**, **right-angle** 5+5, tin over nickel (12.70 x 12.56 x 8.08 mm, 5.8 mm mating pin, 5.08 mm above the PCB) |
| J6-J9 position | Grid in the middle of the top area, cables exit upward | Four headers side by side along the **top board edge** (centres x = -24, -10.6, 2.8, 16.2 mm; y = 25.5; rotated 180 deg), cables exit horizontally |
| Key column | Pins 7/8 pulled, footprint had no holes | Same idea: pins 7/8 pulled, **custom footprint with no holes at 7/8** (8 holes per header, drill 1.05 mm, 1.6 mm pads) |
| Pin map | 1/2 V12S, 3/4 IGN, 5/6 GND, 7/8 key, 9/10 NETi | **Unchanged** |
| Routing | V12S/IGN/NET routed through the middle grid | Whole board re-routed; V12S and IGN buses run above the pad rows; the strip below the pins is trace-free for silk |
| Silk | Row labels at the left of the grid | Per-header column labels under the pins (see below); rev text "Board 2 - Rev 1.1 - 2026-11"; subtitle "Any OBD2 pin to any NET output" |
| J2, J3-J5, J1, SW1, SW2, D2, D3, F2 | | Unchanged |
| Cable housings | 2x5 and 1x5 | 2x5 only (the 1x5 housing no longer fits the right-angle 2x5 face usefully) |

## J6-J9 pin map (identical on every header)

Pins 1 and 2 are in the same column, 3 and 4, and so on; each pair is tied on the board.

| Pins | Signal |
|---|---|
| 1, 2 | V12S |
| 3, 4 | IGN |
| 5, 6 | GND |
| 7, 8 | Key column (pins pulled, no holes) |
| 9, 10 | NETi (NET1 on J6, NET2 on J7, NET3 on J8, NET4 on J9) |

On the board, left to right at the placed rotation: NET (9/10), key (7/8), GND (5/6), IGN (3/4), V12S (1/2). Pin 1 is the square pad at the V12S end.

## Silk labels under J6-J9

Each header has a vertical **SIG_NETn** label (reads bottom to top) directly under its two data pins, just right of the NETn trace, then vertical **GND**, **+12V_IGN** and **+12V_SW** under their columns. The key column is not labelled. J5 keeps its NET1-NET4 labels. Designators J6-J9 sit inside each header's body outline.

## Status and open items

- **Cherry Blossom checks:** no errors; only "unverified part" warnings (J2, J3-J5, F2, and the new J6-J9 footprint, which is built from Harwin's dimensions, not a supplier record).
- **J6-J9 footprint:** verify it against Harwin's M20-974 drawing before fab. The drawing's recommended hole is 1.02 +/- 0.05 mm, pitch 2.54, row spacing 2.54, 0.64 mm square pins, 3.00 mm tail (checked 2026-11-15; the 974 and 995 drawings share the same hole pattern).
- **3D model:** upload `M20-9740546_no-key-pins-7-8.glb` (key pins removed; a mirrored fallback file also exists) to the J6-J9 part in the editor, then check the gap sits next to the NET column. These files derive from Harwin's model; keep them out of the repo.
- **Silk spots to review:** the bottoms of the +12V_IGN labels on J7 and J8 sit very close to J5's NET1 and NET3 labels; a few tented ground vias sit under label strips.
- **Not done:** Gerber export, KiCad regeneration (`hardware/board2-pcb/gen_pcb.py` still builds Rev 1.0), footprint datasheet check, enclosure fit for horizontal cables, JLCPCB order.
- **Ordering note:** the Mouser order already placed contained the Rev 1.0 vertical headers (M20-9980546). Rev 1.1 needs the right-angle M20-9740546 ordered separately (Harwin lists it in stock; Mouser not checked).

## Rev 1.1 buy list (parts that differ or still need buying)

See `hardware/board2-v1.1-bom.csv` (full list) and `hardware/board2-v1.1-bom-mouser.csv` (Mouser upload). The Rev 1.1 changes versus the Rev 1.0 order: **M20-9740546 x4 replaces M20-9980546 x4**, **M20-1070500 goes from 6 to 10** (4 of them as empty dust covers for the pins), and **M20-1060500 is dropped**. M20-003 (x10) and M20-1180046 (x50) are unchanged.
