# Board 2 backlog (ideas parked 2026-11-13, to discuss once the new J4 is on the board)

Context: J4 is being replaced by a Harwin M20 5-row x 8-column grid (four M20-9980546 2x5 headers) per
`~/Downloads/5x8_modular_pcb_connector_spec_bom.md`, built as the doc says first; refinements below come after.

## J4 (Harwin M20 grid) - open questions
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
  No single 5x8 header exists; headers come in 1 and 2 rows only. A 3.5 mm pitch (to match J6/J7) was searched: no unshrouded
  single-row crimp family found (Molex 51067/53258 are shrouded, Ultra-Fit and Hirose MDF6 are dual-row), so J4 stays at 2.54 mm.

## Other
- Silk box and 3D model settings are final for J71, J72, J6 (see REVIEW_BRIEF.md).
- SW1/SW2 terminals, illuminated switches, J2 jack, F2 holder: part choices still open (see `docs/board2-bom.md`).
- Sheet 2 of `diagrams/gems-2pcb-schematic.html` still shows the old layout, J4 and SW pin order.
- BOM still says an 85 x 75 mm board; the board is 87 x 77 mm.
- Routing in Cherry Blossom: not done yet (nets are locked-placement, unrouted).
