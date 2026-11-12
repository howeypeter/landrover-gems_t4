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
| SW1 | 4-pin screw terminal (12V_IN, 12V_OUT, 12V_OUT_LED, GND_LED) | 1 | OPEN | pitch/part not chosen; wires to off-board illuminated switch |
| SW2 | 4-pin screw terminal, same | 1 | OPEN | shared 12V_IGN switch |
| D3 | **1.5KE24A** TVS, 1500 W, 24 V, unidirectional, DO-27 axial | 1 | OK (on hand) | through-hole; leads ~1.0 mm -> **1.3 mm drill** in the KiCad footprint; band to V12S |
| J3 | Amphenol Anytek **OQ1632510000G**, 16-pos 3.81 mm, male shrouded right-angle header (DigiKey 609-3829-ND) | 1 | OK | |
| J3 mate | Amphenol Anytek **TJ1631530000G**, 16-pos, female screw-terminal plug (Board 1 pigtail lands here) | 1 | OK | |
| J7 | Phoenix **SPTAF 1/6-3,5-EL (1862084)** | 2 | OK | 45 deg push-in, 3.5 mm, 16 A/160 V |
| J7 | Phoenix **SPTAF 1/4-3,5-EL (1862068)** | 1 | OK | gang 6+6+4 = 16 pos; verify continuous 3.5 mm pitch when ganged |
| J6 | Phoenix **SPTAF 1/4-3,5-EL (1862068)** | 2 | OK | 2 x 4, rows mirrored (a / b), a/b of each net tied |
| J4 | Molex Micro-Fit 3.0 **43045-0400**, 4-ckt dual-row, right-angle header | 8 | CHECK | 1x8 row along one edge; **verify width vs 85 mm edge (Molex SD-43045-001)**; vertical option 43045-04xx kept as footnote |

## Off-board / cables

| Item | Qty | Status | Notes |
|---|---|---|---|
| Illuminated latching pushbutton, 12 mm, 12 V (built-in lamp; 4 terminals: IN / OUT / LED+ / LED-) | 2 | OPEN | one for SW1 (power), one for SW2 (ignition); 12 V/5 A class |
| Micro-Fit 3.0 receptacle housing, 4-ckt dual-row (mates 43045) | >= 5 (+spares, ~8) | CHECK | believed **43025-0400** — verify in Molex catalog; ECU cable = 3, 10AS cable = 2 |
| Micro-Fit crimp terminals (female) for 20-24 AWG | >= 20 (+spares, ~40) | CHECK | believed 43030-00xx series; needs a Micro-Fit crimper |
| Hook-up wire for device cables | — | OPEN | gauge to suit ~1-2 A; colour-code per net |
| ECU / 10AS mating plugs (C1033, C1017, C225...) | — | OPEN | covered by the bench-rig / pinout docs, not Board 2 |

## Mechanical

| Item | Qty | Status | Notes |
|---|---|---|---|
| PCB, 85 x 75 mm outline, mounting holes (83 x 61 mm pattern per enclosure note) | 1 | OPEN | confirm outline/holes vs the enclosure |
| Standoffs ~1/4" (6 mm) + screws | 4 | OPEN | |
| Enclosure with side cutout for the J4 cables | 1 | OPEN | right-angle J4 exits through a wall |

## Open decisions before ordering

1. **J4 width:** confirm 43045-0400 fits 8 across the edge (and gap for the plugs).
2. **SW1/SW2 terminals + switches:** pick the 4-pin screw terminal and the illuminated switch part numbers.
3. **Micro-Fit plug housings and crimp terminals:** verify the exact part numbers and the crimp tool.
4. **J2 jack** and **F2 holder** types.
