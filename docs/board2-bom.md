# Board 2 — bill of materials (PCB build)

Drafted 2026-11-11 from `diagrams/gems-2pcb-schematic.html` Sheet 2 (Rev F) and
`docs/board2-j2-j7-output-design.md`. Board 2 is a **dumb relay board** (no IC),
built as a **fabbed PCB** (assumed 2026-11-11 since we are moving to KiCad; earlier plan was perfboard first). Board 1 is out of scope.

Status: **OK** = part number confirmed in this design; **CHECK** = chosen but verify
before ordering; **OPEN** = not yet decided/sourced.

## Board-mounted parts

| Ref | Part | Qty | Status | Notes |
|---|---|---|---|---|
| J1 | XINLAIYA **XY308-2.54-2P** (LCSC C557685), 2-pos 2.54 mm (0.1 in) screw terminal; wire to a barrel jack | 1 | CHECK | pitch matches Board 1 (2026-11-14). Listings: 6 A / 150 V, 18-26 AWG (4P datasheet; not checked against the maker PDF). Footprint `TerminalBlock_Xinya_XY308-2.54-2P_1x02_P2.54mm_Horizontal` |
| D2 | Reverse-polarity series diode — **SB540** (5 A/40 V Schottky, DO-201AD axial through-hole) | 1 | OK | chosen 2026-11-11 (~$0.30 at Mouser per user); replaces SS54 (SMD, 5-pc minimum) and 1N5822 (Mouser ~$20). Band (cathode) toward F2/load; footprint DO-201AD |
| F2 | Fuse 2 A (5x20 glass) + PCB holder, covered type (green, cover marked 5X20) | 1 | CHECK | footprint chosen 2026-11-13: Board 1's F1 holder, **pins 15.0 mm apart**, holes **1.3 mm**, body 25.7 x 11.5 x 13.4 mm, pins 4.2 mm long (`board2.pretty/Fuseholder_2pin_5x20_P15mm`). Holder part number still to pick; confirm the pin spacing on the part you buy |
| SW1 | XINLAIYA **XY308-2.54-4P** (LCSC C915913), 4-pos 2.54 mm screw terminal (pin 1 GND_LED, pins 2-3 12V_OUT_LED + 12V_OUT, pin 4 12V_IN; same order and part family as Board 1 J1) | 1 | CHECK | silk name SW1_BAT; wires to off-board illuminated switch. 6 A / 150 V per listings; use 18 AWG for about 3 A |
| SW2 | XINLAIYA **XY308-2.54-4P** (LCSC C915913), same | 1 | CHECK | silk name SW2_IGN; shared 12V_IGN switch |
| D3 | **1.5KE24A** TVS, 1500 W, 24 V, unidirectional, DO-27 axial | 1 | OK (on hand) | through-hole; leads ~1.0 mm -> **1.3 mm drill** in the KiCad footprint; band to VF (F2 output / SW1 input) |
| J2 | Same Sky **TBP02R1-381-16BE**, 16-pos 3.81 mm, right-angle (horizontal) pluggable header, blue | 1 | OK | replaces Amphenol Anytek OQ1632510000G (2026-11-12). Datasheet rev 1.04: holes 1.40 mm, body 61.75 x 9.20 mm, pin row 1.20 mm from the back; 8 A UL / 7 A IEC |
| J2 mate | Same Sky **TBP02P1-381-16BE**, 16-pos, pluggable screw-terminal plug, 180° wire entry (Board 1 pigtail lands here) | 1 | OK | replaces TJ1631530000G; mates the TBP02R1-381 series per the Same Sky mating guide |
| J3/J4 | Same Sky **TBL002A-350-08GR-2OR** (DigiKey 102-6384-ND), 8-pos 3.5 mm 45° push-button, 2 A UL / 5 A IEC | 2 | OK | 2 x 8 = 16 pos (replaces Phoenix SPTAF 6+6+4); datasheet checked 2026-11-11; pins staggered A/B 5.0 mm, drill 1.2 mm |
| J5 | Same Sky **TBL002A-350-08GR-2OR**, 8-pos | 1 | OK | single block: pin pairs 1-2 = NET4, 3-4 = NET3, 5-6 = NET2, 7-8 = NET1 (each pair tied; reassigned 2026-11-14 to match the silk and J6-J9 order); replaces 2 x SPTAF 1/4 |
| J6-J9 | Harwin **M20-9980546**, 2x5 (10-position) 2.54 mm vertical pin header, 3 A/contact | 4 | CHECK | four side by side = a 5-row x 8-column grid (~20.3 x 12.7 mm), cables exit upward. Rows: V12S, IGN, GND, key, NET; columns NET1a NET1b NET2a NET2b NET3a NET3b NET4a NET4b. **Pull the two key-row (row 4) pins from each header (8 in all) before soldering**; the footprint has no row-4 holes. Replaces the 8 Molex Micro-Fit 43045-0412 (2026-11-13). DigiKey, Octopart and LCSC (C3327032) list it; Mouser listing not yet confirmed |

## Off-board / cables

| Item | Qty | Status | Notes |
|---|---|---|---|
| Illuminated latching pushbutton, 12 mm, 12 V (built-in lamp; 4 terminals: IN / OUT / LED+ / LED-) | 2 | OPEN | one for SW1 (power), one for SW2 (ignition); 12 V/5 A class |
| Harwin M20 female crimp housings: **M20-1060500** (1x5, one column) and **M20-1070500** (2x5, two columns) | 6 + 6 | CHECK | 4 active + 2 spare of each. Mouser numbers not confirmed |
| Harwin **M20-003** polarizing key plug | 10 | CHECK | 2 per 2x5 housing (pins 7/8) + 2 spare |
| Female crimp contacts: Harwin **M20-1180046** (loose, tin, 22-30 AWG) | 50 | CHECK | 32 needed (8 per 2x5) + 18 spare; standardised on tin to match the M20-9980546 headers |
| Crimp tool for the M20 contacts | 1 | OPEN | user is buying a ratcheting crimper on Amazon instead of the $600 Harwin Z20-320; confirm it suits 0.64 mm-pin open-barrel contacts |
| Hook-up wire for device cables | — | OPEN | gauge to suit ~1-2 A; colour-code per net |
| ECU / 10AS mating plugs (C1033, C1017, C225...) | — | OPEN | covered by the bench-rig / pinout docs, not Board 2 |

## Mechanical

| Item | Qty | Status | Notes |
|---|---|---|---|
| PCB, 87 x 77 mm outline, 1.6 mm, four M4 holes (4.3 mm, plated) 4.5 mm in from the edges (78 x 68 mm pattern) | 1 | OPEN | corrected 2026-11-14 (was 85 x 75 / 83 x 61 per an old enclosure note); confirm outline/holes vs the enclosure |
| Standoffs ~1/4" (6 mm) + screws | 4 | OPEN | |
| Enclosure with room/opening above J6-J9 for the cables | 1 | OPEN | vertical J6-J9 cables exit upward (lid cutout or tall enough box) |

## Open decisions before ordering

1. **J6-J9:** confirm the Harwin M20-9980546 on Mouser (stock and part number) and the housing/key-plug/contact numbers; ideas parked in `docs/board2-backlog.md`.
2. **Illuminated switches:** pick the part numbers (the SW1/SW2 and J1 terminals are now the 2.54 mm XINLAIYA XY308 series, as on Board 1).
3. **M20 plug housings, key plugs and crimp contacts:** verify the exact part numbers and whether pre-crimped leads fit.
4. **J1 jack** type, and the **F2 holder** part number (type chosen: 5x20 covered, 15 mm pins, as Board 1).
