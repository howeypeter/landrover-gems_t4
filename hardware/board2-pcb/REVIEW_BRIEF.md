# Board 2 (PCB2) — design review brief

Written 2026-11-12 for an external review of the KiCad files in this folder.
It explains what the board is for, what has been decided and why, what state the
files are in, and what we most want checked.

## 0. Work in progress (2026-11-12)

The power section is being rearranged. **F2, D2 and D3 are parked off the board** (to the right) and their traces are removed,
so the power-chain nets (VJ2, VD, VF and the branch to SW1) show as unconnected in DRC on purpose. The layout described in
section 8 for the power row is the previous arrangement. Routing and silkscreen will be redone after the move.

**Files not in the repository (licence).** The J3 footprint and 3D model come from the SamacSys library via Mouser, whose
licence forbids redistributing the models as library components. They are kept local: the SamacSys footprint, our edited copy
of it (`OQ1632510000G_1x16_P3.81mm_RA_PinsReversed.kicad_mod`) and `OQ1632510000G.stp`, plus the Amphenol datasheet PDF. The
footprint is embedded in `board2.kicad_pcb`, so the board opens without them; regenerating with `gen_pcb.py` needs them in
`board2.pretty/` and `board2.3dshapes/`.

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
| J2 | 12 V input, 2-pos | Phoenix MKDS 1,5/2 5.08 mm | **Stand-in.** Jack or terminal not chosen. |
| D2 | SB540, 5 A / 40 V Schottky, DO-201AD | `D_DO-201AD_P12.70mm_Horizontal` | Pin 1 (K) = VD, pin 2 (A) = VJ2. |
| F2 | 2 A fuse + holder | Schurter 0031.8201 5x20 open holder | **Stand-in.** Holder type not chosen. |
| D3 | 1.5KE24A TVS, 1500 W, unidirectional, DO-27 | `D_DO-27_P12.70mm_Horizontal` | Pin 1 (K) = VF. Leads about 1.0 mm; wants about 1.3 mm holes. |
| SW1, SW2 | 4-pos screw terminal | Phoenix MKDS 1,5/4 5.08 mm | **Stand-in.** Part not chosen. |
| J3 | Amphenol Anytek OQ1632510000G (= 20020110-D161A01LF), 16-pos 3.81 mm right-angle shrouded header | edited vendor footprint in `board2.pretty` (SamacSys, via Mouser), with STEP model | 1.40 mm holes, pad numbers mirrored. At the bottom edge rotated 180°: plug opening faces the edge, pins 1 to 16 left to right. |
| J71, J72 | Same Sky TBL002A-350-08GR-2OR, 8-pos 3.5 mm, 45° push-button | custom `board2.pretty` | Together these are "J7". J71 = OBD pins 1–8, J72 = 9–16. |
| J6 | Same Sky TBL002A-350-08GR-2OR | custom `board2.pretty` | Pins 1–4 = NET1a..4a, pins 5–8 = NET1b..4b. |
| J41–J48 | Molex Micro-Fit 3.0 43045-0412, 2x2 vertical through-hole | stock KiCad Molex footprint | J41–J44 = NET1–4 "a" row, J45–J48 = NET1–4 "b" row. |

J4 pinout, identical on all eight headers: **1 = 12V_BAT (V12S), 2 = NET,
3 = 12V_IGN (IGN), 4 = GND.**

Ratings we are relying on: Same Sky TBL002A-350 is 2 A (UL) / 5 A (IEC) per
contact, 20–24 AWG. Micro-Fit 3.0 is about 8.5 A per contact. The fuse is 2 A
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
3. **J2, F2, SW1, SW2 footprints are generic stand-ins** because the real parts
   are not chosen. Layout around them may move.
4. **Molex 43045-0412.** Needs the suffix confirmed against the Molex drawing
   (some suffixes are SMD or have board pegs that need extra holes), and the pin
   numbering confirmed against the mating housing (believed 43025-0400).
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

- **Bottom edge:** J3, centred, plug opening facing the bottom edge. Its footprint (`OQ1632510000G_1x16_P3.81mm_RA_PinsReversed`)
  deliberately numbers the pads right to left in its own frame, so that after the 180° rotation pins read 1 to 16 left to right.
  The Anytek drawing BOQ0602 does not number the pins, so which end is pin 1 is our choice; the pigtail plug must be wired to match
  (OBD pin 1 on the terminal that mates with the J3 silk "1", the left end with the opening toward you).
- **Above J3:** J71 (OBD 1-8, left) and J72 (OBD 9-16, right), at 0°, wire entry facing up toward J6.
- **Middle row, right to left in circuit order:** J2 at the right edge, D2, F2, D3, then SW1 at the left edge. SW2 is below SW1.
  J2, SW1 and SW2 are rotated so wire entry faces the board edge.
- **Above the power row:** J6, centred, rotated 180° so its wire entry faces J7 (the patch wires arrive from below).
- **Top edge:** J4, 2 x 4 grid, centred. Row "a" (J41-J44) above row "b" (J45-J48). Cables leave upward (vertical headers).

Silkscreen: OBD pin numbers on J3 and J7, net names on J6, reference plus net on
each J4 header, a J4 pin legend, +12V/GND at J2, "SW1 POWER", "SW2 IGN".

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
- Confirm Micro-Fit mating housing and crimp terminal part numbers.
- Confirm outline and mounting holes against the enclosure after test-fitting
  Board 1.
- Fix board thickness, copper weight and fab design rules.
- Clean up the routing by hand after review.
