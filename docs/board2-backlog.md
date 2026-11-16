# Board 2 backlog (ideas parked 2026-11-13, to discuss once the new J6-J9 is on the board)

Context: J6-J9 is being replaced by a Harwin M20 5-row x 8-column grid (four M20-9980546 2x5 headers) per
`~/Downloads/5x8_modular_pcb_connector_spec_bom.md`, built as the doc says first; refinements below come after.

## J6-J9 (Harwin M20 grid) - open questions
- **Row 4 key.** Doc: pull the row-4 pin from each header (two per header, eight in all) and put an M20-003 key plug in slot 4 of
  every cable housing. Option: leave the row-4 holes off the footprint (32 holes) so no pin can be fitted.
- **Pin order.** Doc order is V12S, IGN, GND, key, NET (rows 1-5). Checked: key in row 4 blocks a plug turned 180 degrees (it lands on
  the live row-2 pin) and blocks a plug slipped one row either way. A key in the middle row would not block a rotated plug.
- **Column order.** NET1a, NET1b, NET2a, NET2b, NET3a, NET3b, NET4a, NET4b (agreed). a/b of a net are tied on the board.
- **Row 5 meaning.** The doc calls it "K-LINE" in every column and mentions a shared bus; here row 5 is each column's own net.
- **Crimping.** Harwin's own housings take Harwin crimp contacts (M20-1160042 / -1160046 / -1180042 / -1180046, 22-30 AWG). The doc's
  "pre-crimped leads, no crimper" idea assumes generic Dupont-style leads latch in the Harwin housing: not confirmed.
- **Wider plugs.** The doc glues two 5x2 housings for a 5x3 / 5x4 plug. Alternative: a 5x2 plus a 5x1 housing instead of glue.
- **Ratings.** M20 header 3 A per contact, 6.1 mm mating pin, 3.0 mm tail (DigiKey / Octopart listings); our rails are fused at 2 A.
- **K-line pull-up note in the doc** is a Board 1 matter, not Board 2.
- **Verify before ordering:** Harwin datasheet drawings, the M20-003 key plug fit, and the housings' wire range.
- **Retired with this change:** Molex Micro-Fit 43045-0412 (x8), 43025-0400 plug housings, 43030-00xx crimp terminals.
- **Decided 2026-11-13:** four 2x5 headers (M20-9980546), key-row pins pulled and no row-4 holes in the footprint (a 1x8-per-row
  version with four M20-9990846 was built first and set aside: the 2x5 bodies hold the pins together better while soldering).
  No single 5x8 header exists; headers come in 1 and 2 rows only. A 3.5 mm pitch (to match J5/J3/J4) was searched: no unshrouded
  single-row crimp family found (Molex 51067/53258 are shrouded, Ultra-Fit and Hirose MDF6 are dual-row), so J6-J9 stays at 2.54 mm.

## Rev 1.1 idea: right-angle J6-J9 (parked 2026-11-15)
Rev 1.0 went to fab with vertical M20-9980546 headers, so this is for a later revision only.
- **Idea:** horizontal cable exit using the right-angle 5+5 plug Harwin **M20-9950545** ([Harwin page](https://www.harwin.com/products/M20-9950545): 10 contacts, 12.70 x 13.76 x 8.08 mm body, 5.08 mm above the PCB, 0.64 mm pins, 3 A, 3.00 mm tail, gold, cuttable). One 2x5 per NET (NET1-NET4), four along one board edge (about 51 mm of the 87 mm edge).
- **Pin map unchanged:** pins 1/2 V12S, 3/4 IGN, 5/6 GND, 7/8 key (pulled), 9/10 NETi. On the face that is 5 columns (V12S, IGN, GND, key, NET) by 2 rows, the two rows being the tied pair.
- **Mating:** the 2x5 housing M20-1070500 mates (Harwin lists it); the 1x5 housings would cover only one row.
- **Open:** the 9950545 is gold; check for a tin version (M20-9950546 was marked obsolete by one source) or accept gold headers with tin contacts. Needs new footprints, headers moved to the board edge, re-route, Rev bump, re-export of Gerbers, and a repeat of checklist A4. Check enclosure room for horizontal cables.

## Other
- Silk box and 3D model settings are final for J3, J4, J5 (see REVIEW_BRIEF.md).
- SW1/SW2 terminals, illuminated switches, J1 is a screw terminal fed by the user's own barrel jack (settled 2026-11-14): other part choices still open; F2 holder: footprint set (Board 1's F1, 15 mm pins), part number open (see `docs/board2-bom.md`).
- Sheet 2 of `diagrams/gems-2pcb-schematic.html` still shows the old layout, J6-J9 and SW pin order.
- BOM still says an 85 x 75 mm board; the board is 87 x 77 mm.
- Routing in Cherry Blossom: not done yet (nets are locked-placement, unrouted).
- **Verify before ordering (2026-11-14):** wire-entry side of the XY308-2.54 terminals (SW1/SW2 face the left edge, J1 the right edge) against the Xinya datasheet or the 3D model, and the 6 A / 150 V rating against the maker PDF.
- **Open layout notes:** F2 clears J4 by about 1.4 mm (it can not move further without hitting J1/D2); J3 to J4 gap about 1.0 mm; KiCad board is unrouted (routing is done in Cherry Blossom).

