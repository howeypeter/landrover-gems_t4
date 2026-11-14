# Board 2 (PCB2) — design review brief

Written 2026-11-12 for an external review of the KiCad files in this folder.
It explains what the board is for, what has been decided and why, what state the
files are in, and what we most want checked.

## 0. Work in progress (updated 2026-11-13)

The power section has been rearranged (J2, F2, D3 in a column on the right edge, D2 beside J2) and is placed in both KiCad and
Cherry Blossom. Routing in Cherry Blossom has not been done yet; in KiCad the board is routed by `route.py`. The layout
paragraph in section 8 describes the current arrangement.

**F2 changed (2026-11-13).** F2 uses the footprint from Board 1's F1 (`Fuseholder_2pin_5x20_P15mm.kicad_mod`): a covered 5x20
holder, pins 15.0 mm apart, both holes 1.3 mm, body 25.7 x 11.5 mm. The 15 mm spacing is from Board 1's design; the body size
is from a product photo. The holder's part number is not chosen.

**J3 changed (2026-11-12).** J3 is now the Same Sky TBP02R1-381-16BE (mate TBP02P1-381-16BE), replacing the Amphenol Anytek
OQ1632510000G. Its footprint (`SameSky_TBP02R1-381-16BE_1x16_P3.81mm_RA_PinsReversed.kicad_mod`) was written from the Same
Sky datasheet rev 1.04 (3.81 mm pitch, 1.40 mm holes, pin row 1.20 mm from the back, body 61.75 x 9.20 mm) and is in the
repository. The vendor's own footprint from the download matched those numbers.

**Files not in the repository (licence).** The 3D models come from third-party downloads (a distributor and SamacSys via
Mouser) and are kept local: `TBP02R1-381-16BE.step` (the J3 model), the older `OQ1632510000G.stp` and SamacSys footprint
files, and the Amphenol datasheet PDF. The footprints are embedded in `board2.kicad_pcb`, so the board opens without them;
regenerating with `gen_pcb.py` needs the STEP in `board2.3dshapes/`. KiCad 3D model settings for J3: rotate (0, 90, 0),
offset (19.0, -10.1, -2.0) mm; the body then sits on the board and the pins pass through. In Cherry Blossom the model
needed a Z offset of -3.5 mm to sit on the board with the pins through it (confirmed visually 2026-11-12); its rotation and
X/Y offsets are not recorded here. Datasheet pin tail below the housing: 3.50 +/- 0.30 mm.

Cherry Blossom 3D model settings for the Same Sky TBL002A-350-08GR-2OR. They are set on the part itself, so J71, J72 and J6
all take them together (confirmed oriented correctly 2026-11-12; J6's 180° board rotation is applied on top of them): turn
X, Y, Z = 90, 0, 90; offset X, Y, Z = 13 mm, -1.3 mm, -3.7 mm. The vendor STEP is the full 8-pole block (8 push buttons, about 29.3 mm long);
the Same Sky `BOM.txt` description ("Vertical, 3.81 Pitch") is wrong for this part.
Cherry Blossom shows STEP models without colour. A GLB converted from the vendor STEP keeps the colours (green body, orange
buttons, white pins) and lines up exactly with the pinholes (confirmed 2026-11-12). It is made with KiCad:
`kicad-cli pcb export glb --no-board-body --user-origin <footprint origin> -f -o part.glb <test board with the footprint at
rotation 0, model offset 0>`. The GLB is a vendor-licensed model derived from the STEP and is not in the repository.

Orientation on the board (2026-11-13): J71 and J72 are turned 180 degrees (wire entry faces the other way; pins read 1 to 8
right to left, so the OBD lines to J3 cross and need re-routing); J6 is back at 0 degrees (its earlier 180 degrees only
compensated for the part's own orientation). In KiCad these parts are positioned by pad 1 (see `PAD1` in `gen_pcb.py`),
copied from Cherry Blossom.

Final Cherry Blossom settings for the GLB (placed by "The file's origin"; confirmed 2026-11-13: pins in the holes, housing
inside the silk box, buttons on the A-row side): turn X, Y, Z = 90, 0, 270; offset X, Y, Z = 3.5 mm, 2.3 mm, 0 mm. They are
set on the part, so J71, J72 and J6 all take them. The settings in the paragraph above are for the STEP and are superseded.
Lesson: the pad pattern is the same from both ends, so a model turned 180 degrees still lines up with the holes. Check the
housing's long end: the real housing extends 3.25 mm past pin 1 (the square pad, A row) and 1.75 mm past pin 8, verified from
the vendor model's own pin and body geometry. The first attempt (turn Z = 90) was 180 degrees out, so the box looked 1.5 mm off. KiCad has no equivalent settings: its J7/J6
models are still green block stand-ins.

J41-J44 3D model (2026-11-13/14): the Harwin M20-9980546 vendor model (Ultra Librarian download, `M20-9980546.glb` / `.stp`)
is a 2x5 header, 12.7 x 5.08 x 2.64 mm body, 0.66 mm square pins from 3.0 mm below the body underside to 8.64 mm above it
(units are metres in the GLB). Its origin is pin 1 and its long axis runs along x, so it must be spun 90 degrees to match our
footprint (5 pins along y). Placed by "The file's origin", offset 0. In Cherry Blossom the models worked once the spin was on
the third Turn box (a first try with the spin on the wrong axis made the four headers overlap into one 11-pin-wide strip,
22 pins visible); the user's final Cherry Blossom settings (the part rebuilt 2026-11-14 with 1.1 mm holes; GLB re-uploaded) are: offset X, Y, Z = 1.27 mm, -5.08 mm, -3 mm; rotate X, Y, Z = 270, 0, 270 (set on the part, so J41 to J44 all take them). In KiCad the footprint model is
`board2.3dshapes/M20-9980546_KeyRowRemoved.wrl` (rotate z 90, scale 0.3937), the same model with the two key-column pins
(x = 7.62 mm) deleted, so the KEY row is empty. A GLB of the same edited model is next to it. Both derive from the vendor
model and are gitignored.

## 1. How to read this brief

- **Review target:** `board2.kicad_sch` and `board2.kicad_pcb` (KiCad 10).
- **Status:** first complete pass. Schematic passes ERC. PCB is placed, routed and
  passes DRC with 0 errors, but it has **not** been reviewed by a person and has
  **not** been sent to fab.
- **Both files are script-generated** (section 9). Review findings will be applied
  to the scripts, not hand-edited into the files.
- Several footprints are **stand-ins** for parts that are not chosen or not yet
  verified (section 7). Those are the highest-risk items.

## 2. Project context

The project is a home-built diagnostic tool for the engine computer of a
1990s Land Rover Discovery 1 (Lucas/SAGEM "GEMS" V8 engine management). These
vehicles have no CAN bus. Diagnostics run on **K-line** (ISO 9141-2 / KWP2000):
a single-wire, 12 V, open-collector serial bus at about 10.4 kbaud, half duplex.

The system is two boards:

| Board | Role | Status |
|---|---|---|
| Board 1 | The adapter. Raspberry Pi Pico 2 W plus two ST L9637D K-line transceivers. Ends in a male OBD2 (J1962) pigtail. Plugs into a car, or into Board 2. | Finished. Out of scope for this review. |
| **Board 2** | The bench hub. Lets Board 1 talk to modules sitting on a workbench (engine ECU, the Lucas 10AS alarm/immobiliser unit, later others) instead of in a car. | **This review.** |

Signals are slow and low current. There are no impedance, length-matching or
high-speed concerns anywhere on Board 2. The concerns are power protection,
connector correctness, current capacity and mechanical fit.

## 3. What Board 2 is

Board 2 is a **passive wiring board. It has no IC and no active parts** apart
from two protection diodes and a fuse. It does three things:

1. Takes 12 V from a bench supply, protects it, and switches it into two rails
   (battery and ignition).
2. Receives the 16 OBD2 wires from Board 1 on a fixed connector and breaks them
   out to a 16-position patch terminal.
3. Fans four patchable signal nets, plus power and ground, out to eight
   identical keyed output headers that device cables plug into.

The design goal is that **the PCB never changes**. Supporting a new module means
moving patch wires and building a new cable, not a new board.

## 4. Signal chain

```
Board 1 OBD2 plug -> pigtail -> screw-terminal plug -> J3 (16-pos header, fixed)
   -> copper, 1:1 -> J7 (16 push-in terminals, silk = OBD pin 1..16)
   -> loose patch wires (user-fitted) -> J6 (8 push-in terminals: 4 nets x 2)
   -> copper -> J4 (8 keyed 2x2 headers) -> per-device cables
```

- **J3 to J7 is 1:1.** J3 pin n connects to J7 pin n. Exceptions: pin 5 is GND
  and pin 16 is the switched 12 V rail (standard OBD2 positions). Pin 4 (chassis
  ground on OBD2) is deliberately **not** tied to GND on this board; it is just
  net `OBD4`.
- **J7 to J6 has no copper.** The link is a patch wire the user fits. This is
  intentional. In the netlist each `OBDn` net therefore has only two pads.
- **J6** has two terminals per net (a and b), tied together on the board.
- **J4** is eight headers in a 2 x 4 grid. Each header carries one signal net
  plus both power rails and ground. Two headers per net.

### Net names

Board 2 uses neutral names because it does not know which Board 1 channel is
read/write and which is listen-only.

| Net | Normally patched to (Board 1) |
|---|---|
| NET1 | transceiver U2, read/write K-line |
| NET2 | transceiver U2, listen-only tap |
| NET3 | transceiver U3, read/write K-line |
| NET4 | transceiver U3, listen-only tap |

## 5. Power path

```
J2 (+12 V, GND)
  -> D2  SB540 Schottky, series, reverse-polarity protection     net VJ2 -> VD
  -> F2  2 A fuse                                                net VD  -> VF
  -> SW1 terminal -> off-board switch -> back                    net VF  -> V12S
  V12S -> SW2 terminal -> off-board switch -> back               net V12S -> IGN
  D3  1.5KE24A TVS from VF to GND (cathode on VF)
```

| Net | Meaning | Goes to |
|---|---|---|
| VJ2 | raw 12 V input | J2 pin 1, D2 anode |
| VD | after the Schottky | D2 cathode, F2 |
| VF | after the fuse | F2, SW1 pin 1, D3 cathode |
| V12S | switched battery rail ("12V_BAT") | SW1 pins 2+3, SW2 pin 1, J3 pin 16, J72 pin 8 (J7 position 16), every J4 pin 1 |
| IGN | switched ignition rail ("12V_IGN") | SW2 pins 2+3, every J4 pin 3 |
| GND | ground | J2 pin 2, D3 anode, SW1/SW2 pin 4, J3 pin 5, J71 pin 5, every J4 pin 4 |

Decisions and reasons:

- **SW1 and SW2 are not switches.** They are 4-pin screw terminals that wire to
  off-board illuminated latching pushbuttons. Pins: 1 = 12V in, 2 = 12V out,
  3 = lamp +, 4 = lamp −. Pins 2 and 3 are tied on the board, so the lamp lights
  when the switch is on. Pin 4 is GND.
- **SW2 is fed from V12S**, so ignition can only be on when main power is on.
- **D3 sits on VF, not V12S**, so the clamp is present even with SW1 off, and
  the fuse is upstream of it.
- **D2 and D3 are both kept.** They do different jobs (series blocking vs shunt
  clamp). Merging them was considered and rejected.
- **V12S feeds J3 pin 16**, so Board 2 powers Board 1 through the OBD2 12 V pin,
  as a car would. Board 1 has its own 1 A fuse, TVS and buck converter.
- All parts are through-hole by choice (hand soldering, low cost).

## 6. Parts

18 placed components, 24 nets.

| Ref | Part | Footprint in the files | Notes |
|---|---|---|---|
| J2 | 12 V input, 2-pos | XINLAIYA XY308-2.54-2P, 2.54 mm (as Board 1) | Terminal chosen 2026-11-14; wire to a jack. |
| D2 | SB540, 5 A / 40 V Schottky, DO-201AD | `D_DO-201AD_P12.70mm_Horizontal` | Pin 1 (K) = VD, pin 2 (A) = VJ2. |
| F2 | 2 A fuse + holder (5x20 glass fuse, covered holder) | `Fuseholder_2pin_5x20_P15mm` in `board2.pretty` (Board 1's F1 footprint, holes corrected to 1.3 mm) | Pins 15.0 mm apart (inset from the fuse clips), body 25.7 x 11.5 mm. Holder part number not chosen. |
| D3 | 1.5KE24A TVS, 1500 W, unidirectional, DO-27 | `D_DO-27_P12.70mm_Horizontal` | Pin 1 (K) = VF. Leads about 1.0 mm; wants about 1.3 mm holes. |
| SW1, SW2 | 4-pos screw terminal | XINLAIYA XY308-2.54-4P, 2.54 mm (as Board 1 J2) | Chosen 2026-11-14. |
| J3 | Same Sky TBP02R1-381-16BE, 16-pos 3.81 mm right-angle (horizontal) pluggable header, blue; mate TBP02P1-381-16BE | `SameSky_TBP02R1-381-16BE_1x16_P3.81mm_RA_PinsReversed` in `board2.pretty`, built from datasheet rev 1.04, with STEP model | 1.40 mm holes, pad numbers mirrored. At the bottom edge rotated 180°: plug opening faces the edge, pins 1 to 16 left to right. |
| J71, J72 | Same Sky TBL002A-350-08GR-2OR, 8-pos 3.5 mm, 45° push-button | custom `board2.pretty` | Together these are "J7". J71 = OBD pins 1–8, J72 = 9–16. |
| J6 | Same Sky TBL002A-350-08GR-2OR | custom `board2.pretty` | Pins 1–4 = NET1a..4a, pins 5–8 = NET1b..4b. |
| J41–J44 | Harwin M20-9980546, 2x5 2.54 mm vertical pin header, four side by side | custom `Harwin_M20-9980546_2x05_P2.54mm_Vertical_KeyRowRemoved` in `board2.pretty` | One 5-row x 8-column grid; header J4n holds columns 2n-1 and 2n (odd pins left, even pins right). Row-4 (key row) pins are pulled from each header, so the footprint has no row-4 holes (pins 7, 8 absent). |

J4 pinout, rows 1 to 5: **V12S, IGN, GND, key (no pin), NET.** Pins 1,2 = V12S; 3,4 = IGN; 5,6 = GND; 9,10 = NETn.
Columns 1 to 8 are NET1a, NET1b, NET2a, NET2b, NET3a, NET3b, NET4a, NET4b (a and b of a net are the same net).
The cable plug is a Harwin M20 crimp housing with a key plug in slot 4: a plug turned 180 degrees puts its key on the live
IGN pin, and a plug slipped one row hits a live pin too.

Ratings we are relying on: Same Sky TBL002A-350 is 2 A (UL) / 5 A (IEC) per
contact, 20–24 AWG. Harwin M20 is 3 A per contact. The fuse is 2 A
for the whole board.

## 7. Known weak points (please check these first)

1. **Custom Same Sky footprint.** Built by hand from datasheet rev 1.04: 3.5 mm
   pitch, pins staggered in two rows 5.0 mm apart (odd pins y = 0, even pins
   y = 5), 1.2 mm drill, 2.0 mm pads, body 29.5 x 12 mm. The **wire-entry side
   and pin 1 end are an assumption** and have not been compared with the vendor
   footprint or 3D model. If they are mirrored, J6 and J7 face the wrong way.
2. **J3 footprint is the distributor's library footprint** (SamacSys, via Mouser) with two edits: pad numbers mirrored
   (see above) and holes opened to the 1.40 mm the Anytek drawing recommends. Pitch (3.81), end offset (2.5 mm), pin row
   position (1.2 mm from the back wall, 8.0 mm from the mating face) match the drawing. Not yet re-checked by a second person.
3. **J2, SW1, SW2 footprints are generic stand-ins (F2 now has the Board 1 holder footprint)** because the real parts
   are not chosen. Layout around them may move.
4. **Harwin M20-9980546 (J4).** The footprint is hand-built (1.02 mm holes, 1.75 mm pads, pins 7 and 8 left out); not yet
   checked against the Harwin drawing. The Mouser numbers for the header, the cable housings (M20-1060500 / M20-1070500),
   the M20-003 key plug and the crimp contacts are unconfirmed.
5. **Routing is from a home-made grid router** (section 9). It is electrically
   complete and DRC-clean but takes indirect paths and has more vias than a
   person would use.

## 8. PCB facts

| Item | Value |
|---|---|
| Outline | 87 x 77 mm rectangle (same as Board 1, same enclosure family) |
| Mounting holes | 4 x M3 (3.2 mm, plated, with via ring), centres 4.25 mm from each edge, so 78.5 x 68.5 mm apart. Not assigned to a net. Spacing may be nudged after a test fit. |
| Layers | 2 (F.Cu, B.Cu). Thickness and copper weight not yet fixed; assume 1.6 mm, 1 oz. |
| Track widths | power nets (VJ2, VD, VF, V12S, IGN) and routed GND 0.8 mm; signals 0.3 mm |
| Vias | 0.8 mm pad / 0.4 mm drill |
| Clearance | routed with 0.5 mm spacing; GND zone clearance 0.3 mm |
| Ground | GND pour on both layers, thermal-relief pad connections, plus explicit 0.8 mm GND tracks |
| Design rules | KiCad defaults; no custom net classes or fab-specific rules loaded yet |

Layout, origin top-left. Signal flow runs bottom to top, and J3 and J7 both read pins 1 to 16 from left to right
as you look at the board from the top with J3 nearest you:

- **Bottom edge:** J3, centred, plug opening facing the bottom edge. Its footprint (`SameSky_TBP02R1-381-16BE_1x16_P3.81mm_RA_PinsReversed`)
  deliberately numbers the pads right to left in its own frame, so that after the 180° rotation pins read 1 to 16 left to right.
  The Same Sky datasheet does not number the pins, so which end is pin 1 is our choice; the pigtail plug must be wired to match
  (OBD pin 1 on the terminal that mates with the J3 silk "1", the left end with the opening toward you).
- **Above J3:** J71 (OBD 1-8, left) and J72 (OBD 9-16, right), turned 180° (the pin numbers on each run right to left, so
  J3 pin n sits under the same left-to-right position on J7).
- **Right edge (circuit order, top to bottom):** J2 at the top right with D2 beside it, then F2, then D3. SW2 (upper) and SW1 (lower)
  are on the left edge. J2, SW1 and SW2 have their wire entry facing the board edge.
- **Middle:** J6, centred, at 0° (the patch wires come up from J7).
- **Top edge:** J4, a 5-row x 8-column grid of four 2x5 headers (J41-J44), centred. Cables leave upward (vertical headers).

Silkscreen: OBD pin numbers on J3 and J7, net names on J6,
column names (1a to 4b) above the J4 grid and row names (+12V, IGN, GND, KEY, NET) beside it, +12V/GND at J2,
"SW1 POWER", "SW2 IGN" with pin names (GND, LED+, OUT, IN) beside every SW1/SW2 pin.

Check results (2026-11-12):

- **ERC:** 0 violations.
- **DRC:** 0 errors; 5 unconnected items, all from the parked power parts (see section 0); 4 silkscreen warnings
  (text overlapping other silk near J6/J4 and J3 pin 1, and one label clipped by
  a pad's mask opening at J71 pin 4). Reports are in `erc.rpt` and `drc.rpt`.

## 9. How the files are produced

| File | What it is |
|---|---|
| `gen_schematic.py` | Writes `board2.kicad_sch` and `board2.kicad_pro`. Nets are defined by a label on every pin; there are no drawn wires. Same label = same net. |
| `board2.net` | Netlist exported from the schematic. |
| `gen_pcb.py` | Reads `board2.net`, loads footprints, places and rotates them, draws the outline, mounting holes and silkscreen. Writes `board2.kicad_pcb`. |
| `route.py` | A* router on a 0.25 mm grid, two layers, then adds and fills the GND zones. Rewrites `board2.kicad_pcb`. |
| `board2.pretty/`, `board2.3dshapes/`, `fp-lib-table` | Custom Same Sky footprint, a simple block 3D model, and the library table. |
| `board2_schematic.pdf`, `board2_top.png`, `board2_bot.png`, `board2_pcb.svg` | Exports for viewing without KiCad. |

Consequences for a reviewer:

- The schematic looks unusual (labels only, no wires). That is expected.
- Running `gen_pcb.py` or `route.py` overwrites the PCB, so comments are most
  useful as "change X to Y" rather than as edits to the board file.

## 10. What we want reviewed

1. **Schematic correctness** against sections 4 and 5: D2 and D3 polarity, fuse
   position, SW1/SW2 pin use, J3-to-J7 mapping, J4 pinout.
2. **Protection design.** Is SB540 + 2 A fuse + 1.5KE24A on VF a sound
   arrangement for a 12 V bench supply feeding automotive modules? Is the TVS
   voltage a sensible choice against the SB540's 40 V rating and the modules
   downstream? Is anything missing (bulk capacitance, a bleed resistor, a
   power-present indicator)?
3. **Current capacity.** 0.8 mm power tracks and the via count on the power
   path at 2 A; whether 2 A is a sensible fuse value for an engine ECU plus an
   alarm unit plus Board 1; and whether GND return through thermal-relief spokes
   is adequate.
4. **Footprints** listed in section 7, especially the custom Same Sky part and
   the J3 stand-in.
5. **Layout and manufacturability.** Connector spacing for fingers and plug
   bodies (J4 grid pitch is 12 mm x 12.7 mm), clearance of parts and copper from
   the mounting holes and board edge, hole sizes for the DO-201AD and DO-27
   leads, and anything a standard 2-layer fab would reject.
6. **Routing quality.** Paths that should be shortened, vias that can go, and
   anywhere the pour is cut into islands.
7. **Silkscreen.** The 11 warnings, and whether polarity marks for D2, D3 and J2
   are clear enough for hand assembly.

## 11. Open items (known, not yet done)

- Choose real parts for J2, F2 holder, SW1/SW2 terminals and the two illuminated
  switches; replace the stand-in footprints.
- Verify the Same Sky, Anytek and Molex footprints against vendor data.
- Confirm the Harwin M20 numbers on Mouser (header, housings, key plug, contacts).
- Confirm outline and mounting holes against the enclosure after test-fitting
  Board 1.
- Fix board thickness, copper weight and fab design rules.
- Clean up the routing by hand after review.

J4 grid and net silk (2026-11-14, Cherry Blossom is the source, KiCad regenerated to match; the KiCad board is unrouted):
J41 to J44 stay at 0 degrees. Their positions are swapped so that, facing the back (J4 edge) of the board, J41 is on the left and J44 on the right
(J41 at x 6.35, J42 1.27, J43 -3.81, J44 -8.89 in Cherry Blossom coordinates). Row labels (+12V_BAT, +12V_IGN, GND, K_LINE_SIGNAL) and the J41 to J44 names are
turned 180 degrees to read from the J4 edge; NET1 to NET4 sit on the J6 side of each header, turned -90 degrees. J6 has NET4, NET3, NET2, NET1 labels under pin pairs
1-2, 3-4, 5-6, 7-8. J6 was reassigned the same day to match: pin pairs 7-8 = NET1, 5-6 = NET2, 3-4 = NET3, 1-2 = NET4; J41 to J44 carry NET1 to NET4 (J41 at the +x end), so the J6 to J4 ratsnest lines no longer cross.

Layout and silk update (2026-11-14, later): all text reads at 0 degrees (J3 edge) or 90 degrees, no upside-down text. J41 to J44 are at 0 degrees with J41 on the left,
pins 1/2 (+12V_BAT) at the J4 edge, then +12V_IGN, GND, the blank key row, and K_LINE_SIGNAL (pins 9/10, NET1 to NET4 per header, joined to the J6 pin pairs) nearest J6.
D2 is turned 180 degrees (anode on VJ2 toward J2, cathode on VD toward F2) and sits 1.5 mm further from F2; F2 is 6.25 mm higher (clear of J72 by about 1.4 mm);
J2 is at y 25.43 (CB) with +12V below and GND above; D3 is unchanged at the bottom right (an upward move was tried and undone). KiCad is regenerated to match and is unrouted.

Terminal wire entry and board facts (2026-11-14):
- Board 87 x 77 mm, 1.6 mm thick; four M3 mounting holes 4.25 mm in from the edges (top right at KiCad (82.75, 4.25), pad ring about 2.6 mm radius).
- SW1 and SW2 (XINLAIYA XY308-2.54-4P) face the left board edge: the wire entries are on the left of the body, about 2.2 mm from the edge, so switch wires screw in from the side of the board.
  J2 (XY308-2.54-2P) faces the right edge, entries about 2.2 mm from the edge, 3.4 mm below the top-right screw-hole ring. This was read from the footprint silk (funnel slots and
  the entry arrow), NOT checked against the Xinya datasheet or the vendor 3D model: confirm before ordering. If an entry faces the middle, rotate that terminal 180 degrees.
- 2.54 mm terminals rate 6 A / 150 V per distributor listings (not the maker PDF); use 18 AWG for about 3 A.

Design decision (2026-11-14, user): OBD pin 4 (chassis ground) is deliberately NOT tied to GND on Board 2. Only OBD pin 5 (signal ground) is GND, so a dirty
chassis ground can not contaminate Board 1's signal ground. J3 pin 4 goes only to J71 pin 5 (net OBD4).
Pre-routing footprint check (2026-11-14): pitch/drill agree with the Same Sky datasheets for J3 (3.81 mm, 1.40 mm holes) and J6/J71/J72 (3.50 mm, rows 5.0 mm, 1.2 mm holes)
and with Board 1's F1 (15.0 mm, 1.3 mm holes). J41-J44 holes are 1.02 mm for 0.66 mm square pins (diagonal 0.93 mm, only about 0.09 mm margin; Harwin's own footprint uses 1.15 mm).
Cherry Blossom's D2 land has the pads 13.6 mm apart while KiCad's DO-201AD stand-in is 12.7 mm (D3 12.5 vs 12.7): check the real SB540 / 1.5KE24A lead spacing.

J41-J44 3D model settings in Cherry Blossom (2026-11-14, user): offset 1.27 mm, -5.08 mm, -3 mm; rotate 270, 0, 270. Use board2.3dshapes/M20-9980546_KeyRowRemoved.glb (8 pins, key column removed).

