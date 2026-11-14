# Board 2 pre-order checklist (Rev 1.0)

Opened 2026-11-14. Everything below must be handled, or consciously waived, before the boards are ordered from JLCPCB.
Status: OPEN = not done, DECIDE = needs a decision, DONE = finished (date), ACCEPTED = risk knowingly accepted by the user (date). Update this file as items close.

State when opened: Cherry Blossom routed and clean (only the four "unverified part" warnings); KiCad regenerated but unrouted by design;
silk, naming (J1-J9) and M4 holes done; last commit `684d630`.

## A. Must check before ordering

| # | Item | Status | Notes |
|---|---|---|---|
| A1 | J2 footprint (TBP02R1-381-16BE, 16-pos 3.81 mm) vs Same Sky datasheet drawing | DONE (2026-11-14) | Checked against the datasheet PCB layout (rev 1.04): pitch 3.81 OK, hole dia 1.40 OK, 16-pole span 57.15 mm OK (B = 57.15), square pin 0.80 mm. Datasheet: `hardware/board2-pcb/tbp02r1-381.pdf` (vendor file, keep out of the public repo). |
| A2 | J3/J4/J5 footprint (TBL002A-350-08GR-2OR, 8-pos 3.5 mm 45 deg) vs datasheet | DONE (2026-11-14) | Checked against the datasheet PCB layout (rev 1.04): pitch 3.50 OK, rows 5.00 apart OK, hole dia 1.20 OK, 8-pole span 24.50 OK, body depth 12.00 OK. Ratings per contact: 2 A UL / 5 A IEC (V12S fuse is 2 A, so J4 pin 1 sits at the UL figure). Wire range 24-20 AWG, strip 8-9 mm (22 AWG pigtail OK). Wire-entry direction is not clear from the drawing: see A6. |
| A3 | F2 fuse holder footprint (5x20, 15 mm pins) and part number | ACCEPTED (2026-11-14) | Risk accepted by the user: the holder is an Amazon part, the specs given (5x20, 15 mm pins, 1.3 mm holes) are the right ones, so no supplier record or datasheet check is needed. Cherry Blossom will keep showing the "unverified part" warning for it. |
| A4 | J6-J9 Harwin M20-9980546 footprint (key row removed, 1.1 mm holes) | DONE (2026-11-14) | Checked against Harwin drawing M20-998 (active product, 100% tin finish): pitch 2.54 OK, row spacing 2.54 OK, 0.64 mm square pin OK, 3 A OK, tail 3.00 mm. Note: Harwin recommends hole dia 1.02 +/-0.05 (max 1.07); ours is 1.1 (0.03 over), chosen for fab tolerance. The pin diagonal is 0.91 mm so it fits easily. |
| A5 | J1 12 V input: confirm the XY308-2.54-2P terminal (not a barrel jack) | DONE (2026-11-14) | User confirmed: J1 is the screw terminal; the user's own barrel jack has wires that screw into J1. Before first power-up check polarity: jack tip/centre wire to J1 pin 1 (+12V), sleeve wire to J1 pin 2 (GND), as the silk shows. |
| A6 | SW1/SW2/J1 terminals (Xinya XY308): wire-entry direction and 6 A rating vs datasheet | DONE (2026-11-14) | XY308-2.54 datasheet: 150 V / 6 A, 26-18 AWG (1.0 mm2), pitch 2.54 OK, solder pin 0.80 x 0.50 (hole 1.2 OK), tail 3.4, body 8.5 x 6.5. Rating OK. Wire-entry direction: user confirmed the current orientation is correct as-is. |
| A7 | Enclosure fit: 87 x 77 mm outline and 78 x 68 mm M4 hole pattern (centres 4.5 mm from edges) | ACCEPTED (2026-11-14) | User says the holes are good where they are. Not test-fitted; if the hardware-store check of M4 screws against the enclosure shows a problem, reopen this item. Screw-clearance zone is 5.5 mm around each hole centre (9 mm washer + 1 mm offset). |
| A8 | D2 (SB540, DO-201AD) and D3 (1.5KE24A, DO-201) hole sizes vs datasheets | DONE (2026-11-14) | D2 lead dia 1.20-1.30 mm in a 1.6 mm hole OK. D3 lead dia 0.96-1.07 mm in a 1.2 mm hole OK; body 7.2-9.5 mm long x 4.8-5.3 mm dia fits the 12.7 mm pad spacing. (D3 uses the KiCad DO-27 footprint name; the part is DO-201, geometry is what matters.) |

## B. Decisions

| # | Item | Status | Notes |
|---|---|---|---|
| B1 | Small silk: subtitle, rev line, tied-net note were 0.8 mm | DONE (2026-11-14) | User chose to raise them to 1.0 mm (JLCPCB suggests about 1.0 mm height, 0.15 mm stroke). Title block now centred at KiCad x 34 (CB x -9.5), note at x 19.5 (CB x -24). KiCad text stroke is 0.15 mm; KiCad library part-outline lines are 0.12 mm, below the 0.153 mm JLCPCB silk minimum, so check line widths in the Cherry Blossom export (C2). |
| B2 | Mounting-hole rings: plated, 8.0 mm, floating (not tied to GND) | DONE (2026-11-14) | User confirmed: keep floating. |

## C. Needed to publish

| # | Item | Status | Notes |
|---|---|---|---|
| C1 | Export Gerbers/drill from **Cherry Blossom** (not KiCad: KiCad is unrouted) | DONE (2026-11-14) | User exported `~/Downloads/board-2-bench-hub-pcb2.zip` (73.5 KB; F/B copper, mask, silk, paste, edge cuts, PTH drill, fabrication notes, bom.csv, pnp.csv). Kept outside the repo. Re-export after any later change to copper or silk. |
| C2 | Check the export | DONE (2026-11-14) | Checked by reading the files (no Gerber viewer available here; also look at the JLCPCB upload preview). Outline 87 x 77 mm, 1 mm corners. Drills: 49 vias 0.3; 32 x 1.1 (J6-J9); 24 x 1.2 (J3/J4/J5); 26 x 1.4 (J2 and the J1/SW1/SW2 terminals); 2 x 1.3 (F2); 2 x 1.5 (D3); 2 x 1.6 (D2); 4 x 4.3 plated mount holes at +/-39, +/-34 (4.5 mm from the edges). No separate NPTH file (all holes plated). Copper strokes 0.25 and 0.8 mm only, vias 0.6 pad. Solder mask has 92 pad openings per side (vias tented, mount rings open). Silk: all strokes 0.15 mm (the 0.12 mm KiCad outline lines do not appear in the Cherry Blossom export); 57 top texts; bottom silk empty. Fabrication notes: 2 layers, 1.6 mm, 1 oz, HASL, green mask, white silk, 0.25 mm / 0.3 mm smallest features. Note: terminal holes are 1.4 mm and D3 holes 1.5 mm in the export (KiCad footprints use 1.2); both are loose fits for 0.8 x 0.5 mm pins and 1.07 mm leads but leave 0.3-0.45 mm annular rings, which is fine. |
| C3 | JLCPCB order settings | OPEN | Settings to enter: 2 layers; 87 x 77 mm (fits the 100 x 100 mm tier); qty as needed; 1.6 mm thickness; 1 oz outer copper; HASL (lead-free if you prefer); green or any mask; white silk; min track/space 6/6 mil (our rules: 0.25 mm signals, 0.2 mm clearance, 0.8 mm power); min drill 0.3 mm (vias 0.3 drill / 0.6 pad); no castellation, no edge plating; plated mount holes are part of the drill file. |
| C4 | Confirm Rev: `REV = "1.0"`, `REVDATE = "2026-11"` in `gen_pcb.py` and the silk match what is ordered | DONE (2026-11-14) | Silk reads "Board 2 - Rev 1.0 - 2026-11" in both tools. Bump the Rev and re-export if copper or silk changes. |

## D. Optional

| # | Item | Status | Notes |
|---|---|---|---|
| D1 | Re-upload the J6-J9 GLB in Cherry Blossom (offset 1.27, -5.08, -3; rotate 270, 0, 270) | OPEN | User task; affects only the 3D view. |
| D2 | `docs/gems-ecu-pinout.md` has an unrelated uncommitted edit | n/a | Leave it out of Board 2 commits. |
