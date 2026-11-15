# Board 2: J6-J9 cable sourcing (handoff notes)

Written 2026-11-14. Purpose: hand this to another agent to finish choosing and sourcing the cables/mating connectors for the J6-J9 output headers, and to update the BOMs once the user decides.

## Problem

Board 2 Rev 1.0 (passive 87 x 77 mm OBD2 bench breakout) has four output headers, **J6-J9**, each a **Harwin M20-9980546** (2x5, 2.54 mm pitch, 0.64 mm square pins, 3 A, key row removed in our footprint, 1.1 mm holes). The current Mouser BOM (`hardware/board2-bom-mouser.csv`) mates them with Harwin M20 crimp housings, which needs the Harwin **Z20-320** hand crimp tool (about $600). The user wants a cheaper route, ideally ready-made leads.

## Header geometry and pinout (J6-J9, Harwin M20-9980546)

Source: Harwin drawing M20-998 (checked 2026-11-14, checklist A4) and `hardware/board2-pcb/gen_schematic.py`.

**Mechanical / footprint**

| Item | Value |
|---|---|
| Positions | 2 x 5 (10 pins), through-hole, vertical |
| Pitch (along a row) | 2.54 mm |
| Row spacing | 2.54 mm |
| Pin | 0.64 mm square (diagonal 0.91 mm) |
| Pin tail below board | 3.00 mm |
| Current rating | 3 A per contact |
| Finish | 100% tin |
| Harwin recommended hole | 1.02 mm +/- 0.05 (max 1.07) |
| Hole used on Board 2 | 1.1 mm (0.03 over, chosen for fab tolerance; the pin fits easily) |
| Key row | Removed on our footprint: pins 7 and 8 have no holes |

**Grid layout:** the four headers sit side by side as one 5-row x 8-column grid at 2.54 mm pitch. Header i (J6 = first, J9 = last) holds columns 2i+1 and 2i+2. J6 faces NET1, at the -x end, left to right from the front.

**Pin map (same for J6-J9; NETi is NET1 on J6, NET2 on J7, NET3 on J8, NET4 on J9)**

| Pins | Row | Signal |
|---|---|---|
| 1, 2 | 1 | V12S (switched, fused 12 V) |
| 3, 4 | 2 | IGN |
| 5, 6 | 3 | GND |
| 7, 8 | 4 | Key row: pins pulled, no holes, not connected |
| 9, 10 | 5 | NETi (the two pins are tied) |

**What this means for the mating cable:** each housing needs contacts in pins 1-6, 9 and 10, so 8 contacts per 2x5 housing. Pins 7 and 8 stay empty. Each pair is tied on the board, so a single wire to either pin of a pair carries that signal. A key plug (M20-003) goes in the key-row slot; generic housings have no such slot.

## What is in the Mouser BOM today (Harwin M20 route)

| Part | Role |
|---|---|
| M20-9980546 | J6-J9 board headers (2x5) |
| M20-1070500 | 2x5 crimp housing (bare, no contacts) |
| M20-1060500 | 1x5 crimp housing (bare, no contacts) |
| M20-003 | key plug |
| M20-1180042 / M20-1180046 | loose crimp contacts (22-30 AWG) |
| M20-1160042 / M20-1160046 | reeled crimp contacts |
| Z20-320 | Harwin M20 hand crimp tool (about $600) |

Housings are sold bare; contacts are separate; the tool is required to crimp them.

## Search results

**Ready-made M20 leads:** none found in the Mouser / Digi-Key catalogue. Harwin's M20 datasheet mentions a pre-crimped contacts and cable assembly service by enquiry (technical@harwin.com). Not yet contacted.

**Standard 2.54 mm alternatives (no special tool, hand-assembled):**

- Pololu female-female pre-crimped wires: <https://www.pololu.com/category/72/female-female-wires-with-pre-crimped-terminals>. 22 AWG, female crimp pin on each end, 2-packs, about 150 cm. Pololu states they work with its 0.1" crimp housings.
- Pololu 0.1" 2x5 crimp housing, 5-pack: <https://abra-electronics.com/interconnects/connectors/connector-housing/1913-pololu-01-254mm-crimp-connector-housing-2x5-pin-5-pack-1913-pololu.html>. Wire ends are pushed in by hand, no tool.
- Generic Dupont-style housings and pre-crimped leads (Amazon etc.), not researched in detail.

**Compatibility claim (unverified):** a Digi-Key TechForum post (<https://forum.digikey.com/t/dupont-connectors-and-how-to-find-them-from-digi-key/3315>) says the Harwin M20 is very close to Dupont connectors. Both use a 0.64 mm square pin on a 2.54 mm grid, so electrically the header pins should accept either. Pin-for-pin latch and housing fit against the M20-9980546 is **not confirmed**.

## Tradeoffs to weigh

- **Keying:** Pololu/Dupont housings have no key plug slot. Our M20 footprint already has the key row removed, so a 2x5 housing plugs in either way round; the silk and pin-1 marking are the only guard against reversal.
- **Mouser:** Pololu and Dupont items are not Mouser parts, so the Mouser BOM would shrink to the board parts only.
- **Wire gauge:** 22 AWG is fine for signal rows; about 3 A on the power rows (the header rating is 3 A).
- **Fit risk:** the cheap test is to buy one 5-pack of housings and one pack of wires and check they seat and latch on a header before ordering more.

## Options

1. **Pololu route:** 2x5 housings + pre-crimped F-F wires from Pololu. No tool. Remove the Harwin housings, key plug, contacts and Z20-320 from the Mouser BOM.
2. **Harwin custom assembly:** email technical@harwin.com for a quote on pre-crimped M20 leads. Likely slower and priced for volume.
3. **Generic Dupont housing + a cheap ratcheting crimper** (tens of dollars, not $600).
4. **Keep the Harwin M20 route** and accept or skip the tool.

## Decision (2026-11-14)

The user chose option 4: **keep the Harwin M20 loose-crimp route from Mouser** and buy a cheaper ratcheting crimp tool on Amazon instead of the $600 Z20-320. Mouser BOM quantities: M20-9980546 x4, M20-1070500 x6, M20-1060500 x6, M20-003 x10, M20-1180046 x50. Z20-320, the reeled contacts and the gold M20-1180042 are removed; contacts are standardised on tin M20-1180046 to match the tin headers. The BOM, `docs/board2-bom.md` and the checklist (E1, E2) are updated to match.

Open points: confirm the Amazon crimper suits M20 contacts, and confirm the key plug count (the decision note says 2 per 2x5 housing; the earlier BOM said 1 per housing).

## To do for the next agent

1. Ask the user which option they want (or run the cheap fit test first).
2. Update `hardware/board2-bom-mouser.csv` (Mouser template columns; quantities go in **Quantity 1** and **Order Quantity**) and `hardware/board2-bom.csv` / `docs/board2-bom.md` accordingly. Add a short non-Mouser purchase list if Pololu is chosen.
3. Update `docs/board2-order-checklist.md` if the cable parts change (no item covers cables today).
4. Commit and push only if the user asks. Keep vendor-licensed datasheets out of the public repo.

## Related files

- `hardware/board2-bom-mouser.csv`, `hardware/board2-bom.csv`, `docs/board2-bom.md`
- `docs/board2-order-checklist.md` (A4 covers the M20-9980546 footprint check)
- `docs/board2-pcb2-summary.md`, `hardware/board2-pcb/REVIEW_BRIEF.md`
