# PCB2 / Board 2 — consolidated summary (single source of truth)

> **Renamed 2026-11-14 (Rev 1.0).** Connectors were renumbered in signal order. Old -> new: J2 -> J1 (12 V in), J3 -> J2 (OBD2 pigtail), J71/J72 (old "J7") -> J3/J4
> (OBD breakout), J6 -> J5 (patch landing), J4 grid with J41-J44 -> J6-J9 (output headers). SW1, SW2, D2, D3, F2 unchanged. Older entries in the git history and in
> `docs/board2-j2-j7-output-design.md` use the old names.

Saved 2026-11-11. Covers everything decided for Board 2 so far. Supporting files:

- `docs/board2-j2-j7-output-design.md` — design narrative (signal chain, parts, cables)
- `docs/board2-bom.md` and `hardware/board2-bom.csv` — bill of materials
- `diagrams/gems-2pcb-schematic.html` **Sheet 2 (Rev F)** — live schematic + parts table
- Not authoritative / stale: `hardware/j6-patch-bay/` (old KiCad scaffold), Sheet 1 of the schematic,
  `docs/two-board-rig.md` and `docs/board2-bench-hub.md` (two other, unreconciled Board 2 designs)

Board 1 (dual L9637D, Pico 2 W) is finished and out of scope.

## 1. What Board 2 is

A **dumb "telephone relay" wire-operator board — no IC.** It converts Board 1's OBD2 pigtail
wires into bench-device connectors (ECU, 10AS, future BCM/SRS) so the **PCB never changes**.
Only patch wires (J3/J4 to J5) and per-device cables (on J6-J9) change.

Built as a **fabbed PCB** (assumed 2026-11-11; earlier plan was perfboard first). User is OK
hand-soldering and is cost-sensitive. Order of work: finalize docs/diagram, **BOM (current)**,
then KiCad PCB setup.

## 2. Net naming (neutral)

Board 2 does not know read/write vs read-only; that is a Board 1 property. The K-Line/L-Line
wording is retired (the L9637D "L" pin is just a receive-only tap).

| Board 2 net | Board 1 silk | Note |
|---|---|---|
| NET1 | LINE1_U2 R/W | each net has an **a** and **b** terminal tied on the board |
| NET2 | LINE2_U2 RO | NET2/NET4 interchangeable (e.g. 10AS listen tap) |
| NET3 | LINE3_U3 R/W | |
| NET4 | LINE4_U3 RO | |

## 3. Signal chain

```
OBD2 plug -> pigtail -> male plug -> J2 (fixed) -> fixed 1:1 -> J3/J4 (16-pos patch access)
  -> movable patch wires -> J5 (landing, 2 rows x 4 cols, rows mirrored; a/b of each net tied)
  -> fixed traces -> J6-J9 (1x8 row of keyed right-angle 2x2 headers) -> per-device cables
```

- **J1** 12 V DC in. **J2** fixed OBD2 receiver. **J3/J4** fixed 1:1 with J2 (silk = OBD pin 1-16).
- **J5**: `NET1a NET2a NET3a NET4a` over `NET1b NET2b NET3b NET4b`; row a faces left, row b faces
  right. Bracket over each a/b pair in silk.
- **J6-J9**: one header per J5 position (a/b of a net adjacent). Each carries 12V_BAT, 12V_IGN, GND + one
  net pin. Keyed (one orientation, cannot be confused with J2's OBD2 plug). Any cable fits any
  header; a mis-plug only moves the data line (a<->b swap harmless; NET1<->NET3 swap matters).
- Worked patch example in the schematic: J3/J4 pin 7 to J5 NET1a.

## 4. Power

J1 -> D2 (reverse-polarity) -> F2 (2 A) -> SW1 -> **V12S**. V12S feeds J2 pin 16 and every J6-J9 BAT pin.
SW2 gates the shared **12V_IGN** rail to every J6-J9 IGN pin. GND is bussed.

- **SW1 / SW2** = 4-pin screw terminals: pin 1 GND_LED, pins 2-3 12V_OUT_LED + 12V_OUT, pin 4 12V_IN (reversed 2026-11-13 to match Board 1; SW2 input = V12S). 12V_OUT_LED is tied to
  12V_OUT on the board (user confirmed). They wire to off-board illuminated latching switches.
- **R2 / LED1 removed** (switches have their own lamps).
- **D2 = SB540** (5 A/40 V Schottky, DO-201AD axial through-hole, ~$0.30 at Mouser per user). Band
  (cathode) toward F2/load. Replaced SS54 (SMD, Newark 5-pc minimum) and 1N5822 (Mouser ~$20).
- **D3 = 1.5KE24A TVS** (1500 W, 24 V, unidirectional, DO-27), on hand, fitted (no longer DNP). Band to
  VF (between F2 and SW1, so it clamps even with SW1 off), other end GND. Leads ~1.0 mm, so use **1.3 mm holes**.

## 5. Connectors

| Ref | Part | Qty |
|---|---|---|
| J2 | Same Sky TBP02R1-381-16BE, 16-pos 3.81 mm right-angle (horizontal) pluggable header, blue (replaced Amphenol Anytek OQ1632510000G 2026-11-12) | 1 |
| J2 mate | Same Sky TBP02P1-381-16BE pluggable screw-terminal plug (replaced TJ1631530000G) | 1 |
| J3/J4 | Same Sky TBL002A-350-08GR-2OR (8-pos, 3.5 mm, 45° push-button; 2 A UL/5 A IEC) | 2 |
| J5 | Same Sky TBL002A-350-08GR-2OR (single block: pins 1-4 a-row, 5-8 b-row) | 1 |
| J6-J9 | Harwin **M20-9980546**, 2x5 2.54 mm vertical pin header, 3 A/contact; four side by side = a 5 x 8 grid (replaced the 8 Molex Micro-Fit 43045-0412 on 2026-11-13) | 4 |

(Replaced Phoenix SPTAF 2026-11-11 by user choice. Footprint is custom `hardware/board2-pcb/board2.pretty`, built from the Same Sky datasheet: 29.5 x 12 mm body, A/B pin rows 5.0 mm apart, wire entry toward -Y — verify against the vendor footprint/3D model before fab.)

**J6-J9 decision (REVISED 2026-11-13, supersedes the Molex Micro-Fit plan):** a **5-row x 8-column grid at 2.54 mm** built
from **four Harwin M20-9980546 2x5 headers side by side** (about 20.3 x 12.7 mm), after the idea in
`~/Downloads/5x8_modular_pcb_connector_spec_bom.md` (used for the pins and plugs only). Rows 1 to 5: V12S, IGN, GND,
key, NET. Columns 1 to 8: NET1a, NET1b, NET2a, NET2b, NET3a, NET3b, NET4a, NET4b. The key row has no pins: pull the two
row-4 pins from each header (8 in all) before soldering; the footprint has no row-4 holes, so a header with its key pins
still in will not seat. The cable plugs are Harwin M20 crimp housings (1x5 M20-1060500, 2x5 M20-1070500) with an M20-003
key plug in slot 4; a plug turned 180 degrees puts the key on the live IGN pin (row 2), and a plug slipped one row
also hits a live pin. Cables exit **upward**. Open points, and the 1x8-row alternative that was considered, are in
`docs/board2-backlog.md`.

**Board:** 87 x 77 mm (same as Board 1; set 2026-11-12), four M4 mounting holes (4.3 mm drill, plated, 8.0 mm ring, same size as Board 1) 4.5 mm from the edges (centres 78 x 68 mm;
Board 1 hole spacing differs, so confirm against the enclosure). Layout (see `hardware/board2-pcb/gen_pcb.py`):
J6-J9 5x8 grid (four 2x5 headers) centred on the top edge; J5 below it, centred; power parts in the right-hand column
(J1 at the top right, D2 beside it, then F2 and D3 below J1); SW2 above SW1 on the left edge; J3/J4 directly above J2
(turned 180 degrees), J2 centred on the bottom edge. Edge terminals (J1, SW1, SW2) have their wire entry facing the
edge. About 1/4" standoffs. (Layout as of 2026-11-13; earlier text in this file described the previous arrangement.)

## 6. Cables and the immobiliser line

- ECU cable = **3 headers** (ECU needs 4 GND, so the harness doubles GND wires). 10AS cable = **2 headers**.
- **Immobiliser (3-way):** ECU C1017 p26 on one NET3 header, 10AS C225 p15 on the other NET3 header.
  Board 1's LINE3 R/W and LINE4 RO wires land on J5 NET3a/NET3b; all one net, no jumper. Patch only the RO
  wire = listen-only; also patch the R/W wire = drive/test. Board 1's RO hardware can never drive.
- Per module: **ECU** C1033 (4 GND + 12V + 12V_IGN), C1017 (K p23, L p20, immobiliser p26). **10AS**
  GND + 12V_BAT + 12V_IGN (both needed) + immobiliser C225 p15 + diagnostic K C225 p17 (OBD pin 8).
- Future BCM/SRS: build a new cable; the PCB does not change.

## 7. Bill of materials status

OK/confirmed: D2 SB540, D3 (on hand), J2 + mate, J3/J4, J5. CHECK: J6-J9 (Harwin M20-9980546 on Mouser), the M20
plug housings, key plug and crimp contacts. F2: 5x20 covered holder, footprint from Board 1 (15 mm pins, 1.3 mm holes), part number still to pick. OPEN: J1 jack, SW1/SW2 screw terminals, illuminated switches (x2), wire,
PCB, standoffs, enclosure. Full tables in `docs/board2-bom.md`.

Distributor tips: DigiKey and Mouser list Harwin M20 parts by their full number (M20-9980546); Mouser prefixes
Harwin with 855-. Confirm each number on Mouser before ordering.

## 8. Open items / next steps

1. ~~J6-J9 width~~ RESOLVED 2026-11-13: J6-J9 is a 5x8 grid of four Harwin M20-9980546 2x5 headers (see section 5).
   **Schematic Sheet 2 (Rev F) of `diagrams/gems-2pcb-schematic.html` still shows the old Micro-Fit J6-J9: update.**
2. **M20 plug housings (M20-1060500 / M20-1070500), key plug (M20-003) and crimp contacts**
   (M20-1160042 / -1160046 / -1180042 / -1180046): verify the numbers on Mouser and whether pre-crimped leads fit.
3. Pick the two illuminated switches, the J1 barrel jack, and the F2 holder part number (J1/SW1/SW2 terminals are the 2.54 mm XINLAIYA XY308 series since 2026-11-14, as on Board 1).
4. Confirm PCB outline and mounting holes against the enclosure; side cutout for J6-J9 cables.
5. **KiCad (started 2026-11-11):** project `hardware/board2-pcb/` (`board2.kicad_pro`, `board2.kicad_sch`, generated by `gen_schematic.py`; ERC clean, netlist 20 parts / 24 nets, `board2_schematic.pdf`). Refs: J1, D2, F2, SW1, SW2, D3, J2, J3-J73 (J3/J4), J61-J62 (J5 rows a/b), J6-J48 (J6-J9; J6-J9 row a NET1-4, J45-48 row b). J6-J9 pins: 1 BAT, 2 NET, 3 IGN, 4 GND. Placeholder footprints (replace): SPTAF (stock Phoenix SPT 1.5), J2 (stock Phoenix MC 1.5 16-pos 3.81), J1, SW1/SW2, F2. **Next:** board outline 85x75, mounting holes, place J3/J4/J5/J6-J9, update PCB from schematic, route. (original note: KiCad PCB setup (KiCad 10: `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`, not on PATH).

   **PCB (2026-11-12):** `gen_pcb.py` (outline 90x80, placement from `board2.net`) then `route.py` (own 2-layer grid router, GND = pour on both layers, V12S/IGN/VJ2/VD/VF 0.8 mm, signals 0.3 mm, vias 0.8/0.4) produce `board2.kicad_pcb`. Run both with KiCad's python; they overwrite the PCB. DRC: 0 errors, 0 unconnected, 5 silk/thermal warnings. Custom footprint `board2.pretty/SameSky_TBL002A-350-08...` (verify vs vendor). Routing is functional but not pretty; review in KiCad before fab.
6. Housekeeping: old A1/A2/A3/B1/B2/B3 names in `PCB_Board_Scheme.md` and `two-board-rig.md` should be
   corrected to Board 1's real silk; reconcile the three Board 2 designs; refresh the stale Sheet 1 and
   the `hardware/j6-patch-bay/` scaffold.

## 9. Git state

Last commit: `6e6a480` (BOM added). **Uncommitted:** `docs/board2-bom.md`, `diagrams/gems-2pcb-schematic.html`
(D2 = SB540), `hardware/board2-bom.csv` (new; see note below), and this file. Not committed unasked.

**Known issue:** `hardware/board2-bom.csv` currently has a mangled D2 line from a bad text replace, and
could not be rewritten because the file is locked (likely open in Excel). Close it and ask for a rewrite;
the correct D2 row is `D2,Diodes Inc./onsemi/any,SB540,5A 40V Schottky through-hole DO-201AD,1,chosen`.
The two 1862068 rows can also be merged into one row, quantity 3.

## How to use the tied NETs (J5 pairs)

Each NET has two J5 terminals joined together (1+2 = NET1, 3+4 = NET2, 5+6 = NET3, 7+8 = NET4), and that NET also goes to pins 9/10 of its J6-J9 header
(J6 = NET1 ... J9 = NET4). A NET can therefore take two wires, which is useful for:

1. **A wire that does not come from the OBD2 connector.** Example: the 10AS to ECU mobilise wire (10AS C225 pin 15 to ECU C1017 pin 26). Land it on a NET
   terminal and it reaches the output headers without passing through J2/J3/J4.
2. **K-line and L-line on one NET.** Land OBD pin 7 (K) and OBD pin 15 (L) on the same NET and they become one node, the same tie Board 1 makes to keep the
   GEMS 0xDA channel open. This frees the second L9637D on Board 1 for a different K-line.

Caution: the two terminals of a NET are shorted together, so any two wires landed on one NET are shorted to each other. That is the intent for K+L (both are
read/driven through one transceiver), but do not land two driven outputs on one NET. The silk on the board reads "J5 pairs tied: 2 wires per NET".
