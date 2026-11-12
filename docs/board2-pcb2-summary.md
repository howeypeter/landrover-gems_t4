# PCB2 / Board 2 — consolidated summary (single source of truth)

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
Only patch wires (J7 to J6) and per-device cables (on J4) change.

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
OBD2 plug -> pigtail -> male plug -> J3 (fixed) -> fixed 1:1 -> J7 (16-pos patch access)
  -> movable patch wires -> J6 (landing, 2 rows x 4 cols, rows mirrored; a/b of each net tied)
  -> fixed traces -> J4 (1x8 row of keyed right-angle 2x2 headers) -> per-device cables
```

- **J2** 12 V DC in. **J3** fixed OBD2 receiver. **J7** fixed 1:1 with J3 (silk = OBD pin 1-16).
- **J6**: `NET1a NET2a NET3a NET4a` over `NET1b NET2b NET3b NET4b`; row a faces left, row b faces
  right. Bracket over each a/b pair in silk.
- **J4**: one header per J6 position (a/b of a net adjacent). Each carries 12V_BAT, 12V_IGN, GND + one
  net pin. Keyed (one orientation, cannot be confused with J3's OBD2 plug). Any cable fits any
  header; a mis-plug only moves the data line (a<->b swap harmless; NET1<->NET3 swap matters).
- Worked patch example in the schematic: J7 pin 7 to J6 NET1a.

## 4. Power

J2 -> D2 (reverse-polarity) -> F2 (2 A) -> SW1 -> **V12S**. V12S feeds J3 pin 16 and every J4 BAT pin.
SW2 gates the shared **12V_IGN** rail to every J4 IGN pin. GND is bussed.

- **SW1 / SW2** = 4-pin screw terminals: 12V_IN, 12V_OUT, 12V_OUT_LED, GND_LED. 12V_OUT_LED is tied to
  12V_OUT on the board (user confirmed). They wire to off-board illuminated latching switches.
- **R2 / LED1 removed** (switches have their own lamps).
- **D2 = SB540** (5 A/40 V Schottky, DO-201AD axial through-hole, ~$0.30 at Mouser per user). Band
  (cathode) toward F2/load. Replaced SS54 (SMD, Newark 5-pc minimum) and 1N5822 (Mouser ~$20).
- **D3 = 1.5KE24A TVS** (1500 W, 24 V, unidirectional, DO-27), on hand, fitted (no longer DNP). Band to
  V12S, other end GND. Leads ~1.0 mm, so use **1.3 mm holes**.

## 5. Connectors

| Ref | Part | Qty |
|---|---|---|
| J3 | Amphenol Anytek OQ1632510000G (DigiKey 609-3829-ND), 16-pos 3.81 mm male right-angle shrouded | 1 |
| J3 mate | TJ1631530000G female screw-terminal plug | 1 |
| J7 | Phoenix SPTAF 1/6-3,5-EL (1862084) | 2 |
| J7 | Phoenix SPTAF 1/4-3,5-EL (1862068) | 1 |
| J6 | Phoenix SPTAF 1/4-3,5-EL (1862068) | 2 |
| J4 | Molex Micro-Fit 3.0 **43045-0412**, 4-ckt dual-row, **vertical** through-hole, 3.00 mm pitch, ~8.5 A (revised from right-angle 43045-0400) | 8 |

(Total Phoenix: 2x 1862084 + 3x 1862068. User mentioned Newark codes 14AC7464 and 14AC7456; the
code-to-MPN mapping is unverified.)

**J4 decision (REVISED 2026-11-11, supersedes the 1x8 right-angle plan):** **8x vertical Micro-Fit
43045-0412 (through-hole, 2x2, 3.00 mm pitch, 1.02 mm drills) as a 2x4 grid**: row a on top, row b mirrored
below, nets in a middle channel (the Rev E layout). Reason: the stock KiCad 43045-0400 right-angle footprint
has an 11.16 mm-wide courtyard, so 8 in a row need ~89 mm and do not fit the 85 mm edge. The vertical
courtyard is 11.16 x 9.78 mm, so the 2x4 grid is ~45 x 20 mm. Cables now exit **upward** (not sideways),
so no side-wall cutout is required. 0412 vs other suffixes (0415 is SMD, 0418 etc. have mounting pegs):
**verify the exact suffix and peg need against the Molex drawing before ordering.** Mating housing
unchanged (43025-0400). Mini-Fit Jr was considered and not chosen. The 1x8 right-angle option is the footnote now.

**Board:** 85 x 75 mm. J7 on one 85 mm long edge, J4 on the opposite long edge; J2 and the SW1/SW2
terminals on the short edges. Enclosure note: internal perfboard 70 x 90 mm, mounting holes 83 x 61 mm,
about 1/4" standoffs.

## 6. Cables and the immobiliser line

- ECU cable = **3 headers** (ECU needs 4 GND, so the harness doubles GND wires). 10AS cable = **2 headers**.
- **Immobiliser (3-way):** ECU C1017 p26 on one NET3 header, 10AS C225 p15 on the other NET3 header.
  Board 1's LINE3 R/W and LINE4 RO wires land on J6 NET3a/NET3b; all one net, no jumper. Patch only the RO
  wire = listen-only; also patch the R/W wire = drive/test. Board 1's RO hardware can never drive.
- Per module: **ECU** C1033 (4 GND + 12V + 12V_IGN), C1017 (K p23, L p20, immobiliser p26). **10AS**
  GND + 12V_BAT + 12V_IGN (both needed) + immobiliser C225 p15 + diagnostic K C225 p17 (OBD pin 8).
- Future BCM/SRS: build a new cable; the PCB does not change.

## 7. Bill of materials status

OK/confirmed: D2 SB540, D3 (on hand), J3 + mate, J7, J6. CHECK: J4 (width), J4 mating housing, crimp
terminals. OPEN: J2 jack, F2 fuse + holder, SW1/SW2 screw terminals, illuminated switches (x2), wire,
PCB, standoffs, enclosure. Full tables in `docs/board2-bom.md`.

Distributor tips: DigiKey lists Molex numbers without hyphens (0430250400). The earlier upload that could
not find 43025-0400 was likely MPN format or stock; check 43020-0400 too.

## 8. Open items / next steps

1. ~~J4 width~~ RESOLVED 2026-11-11: right-angle 1x8 does not fit 85 mm; moved to vertical 2x4 grid
   (43045-0412). Still verify the part suffix/pegs. **Schematic Sheet 2 (Rev F) and the J4 text in
   `board2-j2-j7-output-design.md` still show the old 1x8 right-angle layout: update to the 2x4 grid.**
2. **Micro-Fit plug housing and crimp terminal part numbers** (43025-0400 / 43030-xxxx), wire gauge,
   and a Micro-Fit crimper.
3. Pick SW1/SW2 4-pin screw terminals, the two illuminated switches, J2 jack, F2 holder.
4. Confirm PCB outline and mounting holes against the enclosure; side cutout for J4 cables.
5. **KiCad (started 2026-11-11):** project `hardware/board2-pcb/` (`board2.kicad_pro`, `board2.kicad_sch`, generated by `gen_schematic.py`; ERC clean, netlist 20 parts / 24 nets, `board2_schematic.pdf`). Refs: J2, D2, F2, SW1, SW2, D3, J3, J71-J73 (J7), J61-J62 (J6 rows a/b), J41-J48 (J4; J41-44 row a NET1-4, J45-48 row b). J4 pins: 1 BAT, 2 NET, 3 IGN, 4 GND. Placeholder footprints (replace): SPTAF (stock Phoenix SPT 1.5), J3 (stock Phoenix MC 1.5 16-pos 3.81), J2, SW1/SW2, F2. **Next:** board outline 85x75, mounting holes, place J7/J6/J4, update PCB from schematic, route. (original note: KiCad PCB setup (KiCad 10: `C:\Program Files\KiCad\10.0\bin\kicad-cli.exe`, not on PATH).
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
