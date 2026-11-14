# Board 2 pre-order checklist (Rev 1.0)

Opened 2026-11-14. Everything below must be handled, or consciously waived, before the boards are ordered from JLCPCB.
Status: OPEN = not done, DECIDE = needs a decision, DONE = finished (date). Update this file as items close.

State when opened: Cherry Blossom routed and clean (only the four "unverified part" warnings); KiCad regenerated but unrouted by design;
silk, naming (J1-J9) and M4 holes done; last commit `684d630`.

## A. Must check before ordering

| # | Item | Status | Notes |
|---|---|---|---|
| A1 | J2 footprint (TBP02R1-381-16BE, 16-pos 3.81 mm) vs Same Sky datasheet drawing | OPEN | Hole 1.40 mm / pitch 3.81 agreed earlier; no supplier record in Cherry Blossom, so compare by hand. Datasheet: `hardware/board2-pcb/tbp02r1-381.pdf` (vendor file, keep out of the public repo). |
| A2 | J3/J4/J5 footprint (TBL002A-350-08GR-2OR, 8-pos 3.5 mm 45 deg) vs datasheet | OPEN | Rows 5.0 mm, 1.2 mm holes agreed earlier; no supplier record. Confirm wire-entry direction too. |
| A3 | F2 fuse holder footprint (5x20, 15 mm pins) and part number | OPEN | Part number never confirmed; no supplier record. 1.3 mm holes kept on purpose. |
| A4 | J6-J9 Harwin M20-9980546 footprint (key row removed, 1.1 mm holes) | OPEN | Hand-built; no supplier pinout. Check pitch, hole and pad against the Harwin drawing. |
| A5 | J1 12 V input: confirm the XY308-2.54-2P terminal (not a barrel jack) | DECIDE | BOM still says "jack type OPEN". |
| A6 | SW1/SW2/J1 terminals (Xinya XY308): wire-entry direction and 6 A rating vs datasheet | OPEN | Both were left unverified. |
| A7 | Enclosure fit: 87 x 77 mm outline and 78 x 68 mm M4 hole pattern (centres 4.5 mm from edges) | OPEN | Not test-fitted. Board 1 hole spacing differs. Screw-clearance zone is 5.5 mm around each hole centre. |

## B. Decisions

| # | Item | Status | Notes |
|---|---|---|---|
| B1 | Small silk: subtitle, rev line, tied-net note are 0.8 mm; OBD pin numbers 0.8-0.9 mm | DECIDE | JLCPCB suggests about 1.0 mm height / 0.15 mm stroke. Raise to 1.0 (crowds a few spots) or order and look. |
| B2 | Mounting-hole rings: plated, 8.0 mm, floating (not tied to GND) | DECIDE | Chosen 2026-11-14 as plated and floating; confirm. |

## C. Needed to publish

| # | Item | Status | Notes |
|---|---|---|---|
| C1 | Export Gerbers/drill from **Cherry Blossom** (not KiCad: KiCad is unrouted) | OPEN | Editor's Export menu. |
| C2 | Open the export in a Gerber viewer: pours, 0.8 mm power traces, M4 rings, silk, board outline | OPEN | |
| C3 | JLCPCB order settings: 2 layers, 87 x 77 mm (100 x 100 tier), 1.6 mm, 1 oz, HASL, 6 mil rules, min drill 0.3 | OPEN | |
| C4 | Confirm Rev: `REV = "1.0"`, `REVDATE = "2026-11"` in `gen_pcb.py` and the silk match what is ordered | OPEN | Bump REV for any copper or silk change sent to the fab. |

## D. Optional

| # | Item | Status | Notes |
|---|---|---|---|
| D1 | Re-upload the J6-J9 GLB in Cherry Blossom (offset 1.27, -5.08, -3; rotate 270, 0, 270) | OPEN | User task; affects only the 3D view. |
| D2 | `docs/gems-ecu-pinout.md` has an unrelated uncommitted edit | n/a | Leave it out of Board 2 commits. |
