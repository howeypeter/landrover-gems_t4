# Board 2 — bill of materials (PCB build)

Drafted 2026-11-11 from `diagrams/gems-2pcb-schematic.html` Sheet 2 (Rev F) and
`docs/board2-j2-j7-output-design.md`. Board 2 is a **dumb relay board** (no IC),
built as a **fabbed PCB** (assumed 2026-11-11 since we are moving to KiCad; earlier plan was perfboard first). Board 1 is out of scope.

Status: **OK** = part number confirmed in this design; **CHECK** = chosen but verify
before ordering; **OPEN** = not yet decided/sourced.

## Board-mounted parts

| Ref | Part | Qty | Status | Notes |
|---|---|---|---|---|
| J2 | 12 V DC input jack (barrel or 2-pos terminal) | 1 | OPEN | match the bench supply plug (size/polarity); not specified yet |
| D2 | Reverse-polarity series diode — **SB540** (5 A/40 V Schottky, DO-201AD axial through-hole) | 1 | OK | chosen 2026-11-11 (~$0.30 at Mouser per user); replaces SS54 (SMD, 5-pc minimum) and 1N5822 (Mouser ~$20). Band (cathode) toward F2/load; footprint DO-201AD |
| F2 | Fuse 2 A + holder | 1 | OPEN | holder type (5x20 / blade) not chosen |
| SW1 | 4-pin screw terminal (pin 1 GND_LED, pins 2-3 12V_OUT_LED + 12V_OUT, pin 4 12V_IN; same order as Board 1) | 1 | OPEN | pitch/part not chosen; wires to off-board illuminated switch |
| SW2 | 4-pin screw terminal, same | 1 | OPEN | shared 12V_IGN switch |
| D3 | **1.5KE24A** TVS, 1500 W, 24 V, unidirectional, DO-27 axial | 1 | OK (on hand) | through-hole; leads ~1.0 mm -> **1.3 mm drill** in the KiCad footprint; band to VF (F2 output / SW1 input) |
| J3 | Same Sky **TBP02R1-381-16BE**, 16-pos 3.81 mm, right-angle (horizontal) pluggable header, blue | 1 | OK | replaces Amphenol Anytek OQ1632510000G (2026-11-12). Datasheet rev 1.04: holes 1.40 mm, body 61.75 x 9.20 mm, pin row 1.20 mm from the back; 8 A UL / 7 A IEC |
| J3 mate | Same Sky **TBP02P1-381-16BE**, 16-pos, pluggable screw-terminal plug, 180° wire entry (Board 1 pigtail lands here) | 1 | OK | replaces TJ1631530000G; mates the TBP02R1-381 series per the Same Sky mating guide |
| J7 | Same Sky **TBL002A-350-08GR-2OR** (DigiKey 102-6384-ND), 8-pos 3.5 mm 45° push-button, 2 A UL / 5 A IEC | 2 | OK | 2 x 8 = 16 pos (replaces Phoenix SPTAF 6+6+4); datasheet checked 2026-11-11; pins staggered A/B 5.0 mm, drill 1.2 mm |
| J6 | Same Sky **TBL002A-350-08GR-2OR**, 8-pos | 1 | OK | single block: pins 1-4 = NET1a..NET4a, pins 5-8 = NET1b..NET4b (a/b tied); replaces 2 x SPTAF 1/4 |
| J4 | Harwin **M20-9980546**, 2x5 (10-position) 2.54 mm vertical pin header, 3 A/contact | 4 | CHECK | four side by side = a 5-row x 8-column grid (~20.3 x 12.7 mm), cables exit upward. Rows: V12S, IGN, GND, key, NET; columns NET1a NET1b NET2a NET2b NET3a NET3b NET4a NET4b. **Pull the two key-row (row 4) pins from each header (8 in all) before soldering**; the footprint has no row-4 holes. Replaces the 8 Molex Micro-Fit 43045-0412 (2026-11-13). DigiKey, Octopart and LCSC (C3327032) list it; Mouser listing not yet confirmed |

## Off-board / cables

| Item | Qty | Status | Notes |
|---|---|---|---|
| Illuminated latching pushbutton, 12 mm, 12 V (built-in lamp; 4 terminals: IN / OUT / LED+ / LED-) | 2 | OPEN | one for SW1 (power), one for SW2 (ignition); 12 V/5 A class |
| Harwin M20 female crimp housings: **M20-1060500** (1x5, one column) and **M20-1070500** (2x5, two columns) | as needed | CHECK | ECU cable = 3 columns (a 2x5 plus a 1x5), 10AS cable = 2 columns (one 2x5). Mouser numbers not confirmed |
| Harwin **M20-003** polarizing key plug | one per housing | CHECK | goes in slot 4 (the key row) of every cable housing |
| Female crimp contacts: Harwin M20-1160042 / -1160046 / -1180042 / -1180046 (22-30 AWG), or pre-crimped leads | 4 per column of cable | CHECK | whether generic pre-crimped leads latch in the Harwin housing is unconfirmed |
| Hook-up wire for device cables | — | OPEN | gauge to suit ~1-2 A; colour-code per net |
| ECU / 10AS mating plugs (C1033, C1017, C225...) | — | OPEN | covered by the bench-rig / pinout docs, not Board 2 |

## Mechanical

| Item | Qty | Status | Notes |
|---|---|---|---|
| PCB, 85 x 75 mm outline, mounting holes (83 x 61 mm pattern per enclosure note) | 1 | OPEN | confirm outline/holes vs the enclosure |
| Standoffs ~1/4" (6 mm) + screws | 4 | OPEN | |
| Enclosure with room/opening above J4 for the cables | 1 | OPEN | vertical J4 cables exit upward (lid cutout or tall enough box) |

## Open decisions before ordering

1. **J4:** confirm the Harwin M20-9980546 on Mouser (stock and part number) and the housing/key-plug/contact numbers; ideas parked in `docs/board2-backlog.md`.
2. **SW1/SW2 terminals + switches:** pick the 4-pin screw terminal and the illuminated switch part numbers.
3. **M20 plug housings, key plugs and crimp contacts:** verify the exact part numbers and whether pre-crimped leads fit.
4. **J2 jack** and **F2 holder** types.
