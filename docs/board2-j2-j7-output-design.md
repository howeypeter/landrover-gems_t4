# Board 2 — J2–J7 "wire operator board" design (session context)

**Status: working design, updated 2026-11-11 (rev 3) — Board 2 is a DUMB relay board
(no IC): 4 neutral nets, J6 landing strip + J4 keyed output headers. Not yet
reconciled with the other two Board 2 designs (see end).** The live schematic
`diagrams/gems-2pcb-schematic.html` Sheet 2 (Rev G) matches this doc; the
`hardware/j6-patch-bay/` KiCad scaffold is still the OLD layout.

## Principle

Board 2 is a telephone-exchange-style relay: it converts Board 1's OBD2 wires into
bench-friendly connectors. No IC, nothing active. It does NOT know whether a net is
read/write or read-only — that is a Board 1 property (U2/U3 L9637D). So Board 2 nets
use neutral names, **NET1..NET4**, matching Board 1's silk:

| Board 2 net | Board 1 silk | Meaning (Board 1's concern, not Board 2's) |
|---|---|---|
| NET1 | LINE1_U2 R/W | U2 read/write (two terminals, one net) |
| NET2 | LINE2_U2 RO | U2 listen-only |
| NET3 | LINE3_U3 R/W | U3 read/write (two terminals, one net) |
| NET4 | LINE4_U3 RO | U3 listen-only |

(Board 1's terminals are silk-labelled `+12V_BAT, SIG_GND, LINE1_U2 R/W x2,
LINE2_U2 RO, LINE3_U3 R/W x2, LINE4_U3 RO`. The older A1/A2/A3/B1/B2/B3 names in
`PCB_Board_Scheme.md` / `two-board-rig.md` are out of date vs the silk — TODO fix.)
The old K-Line / L-Line / "L9637D L-pin" wording is retired: the chip's "L" pin is
just a receive-only tap, not an L-line.

## Signal chain

```
Board 1 OBD2 plug -> OBD pigtail -> male plug -> J3 (fixed)
   -> [fixed 1:1] -> J7 (16-pos, patch access; silk = OBD pin numbers 1-16)
   -> [movable patch wires] -> J6 (2x4 landing: rows a/b mirrored)
   -> [fixed traces, NETxa/NETxb tied] -> J4 (2x4 grid of vertical keyed headers)
   -> [per-device patch cables] -> ECU / 10AS / future BCM, SRS...
```

- **J2** 12V DC jack in. **J3** fixed OBD2 receiver. **J7** fixed 1:1 to J3.
- **J6** — 2 rows x 4 columns, rows MIRRORED (row a faces one way, row b the other so wires enter from each side): `NET1a NET2a NET3a NET4a` over `NET1b NET2b NET3b NET4b` (each column = one net, a above b).
  `NETxa` and `NETxb` are tied (same copper net) — two access points per net.
  Silk: bracket over each a/b pair.
- **J4** — 2x4 grid of keyed 2x2 VERTICAL headers (row a on top, row b mirrored, nets in the middle channel; cables exit upward; one per J6 position, a/b of each net a column). Each carries 12V_BAT, 12V_IGN,
  GND + that position's one net pin. J6 NETxa/b and J4 NETxa/b are all one net (fixed traces).
- Power/GND bussed to every J4 header from J2/SW1/SW2 (SW2 = shared IGN switch).
- Only wires at J7/J6 and the cables on J4 ever change; **the PCB never changes**.

## Confirmed parts

- J3: Amphenol Anytek OQ1632510000G (header, 609-3829-ND) + TJ1631530000G (plug), 16-pos 3.81mm.
- J7: 2x SPTAF 1/6-3,5-EL (1862084) + 1x SPTAF 1/4-3,5-EL (1862068), 45 deg, 3.5mm.
- J6: **2x SPTAF 1/4-3,5-EL, Phoenix 1862068** (same part as J7's 4-pos block; 45 deg, 3.5mm, push-in, 16A/160V), mounted as two mirrored rows (or ~10-15mm apart facing the same way — verify 45 deg wire-entry geometry on the datasheet). ~14mm wide. (The 8-pos 1862107 was the earlier single-row option.)
- **J4 (REVISED 2026-11-11, supersedes the 1x8 right-angle plan): 8x Molex Micro-Fit 3.0 `43045-0412`** — 4-circuit dual-row, 3.00mm pitch, **vertical through-hole** (1.02mm drills), laid out as a **2x4 grid** (~45 x 20mm; courtyard 11.16 x 9.78mm each): row a on top, row b mirrored below, nets in a middle channel. Reason: the right-angle `43045-0400` has an 11.16mm-wide courtyard, so 8 in a row need ~89mm, more than the 85mm edge. Cables exit upward (no side-wall cutout; enclosure needs an opening above J4). **TO VERIFY from the Molex drawing:** suffix and whether mounting pegs are wanted (0415 = SMD, 0418 = with pegs).
- **Footnote — dropped option:** the 1x8 right-angle row (43045-0400 x8) — only if the board were widened to ~95mm. Mini-Fit Jr (5566/5557, ~9A, larger) was considered and not chosen.- Board 85x75mm; J7 on one 85mm long edge, J4 grid toward the opposite edge; J2 / switch terminals on the short edges.

## J4 cables / notes

- Pin layout per header: top row 12V_BAT + net pin, bottom row 12V_IGN + GND.
- ECU cable = 3 headers (e.g. NET1a, NET1b, NET3a); ECU needs 4 GND so the harness
  doubles up GND wires. 10AS cable = 2 headers (NET3b + one RO net; see open items).
- All headers identical -> any cable fits any header; a mis-plug only moves the data
  line (power/GND identical). a<->b swaps are harmless (tied); NET1<->NET3 swaps matter.
  Mitigate with silk labels + cable colours.

## Immobiliser line (3-way) — free join via the a/b tie

ECU immobiliser line (C1017 p26) on a NET3 header; 10AS (C225 p15) on the other NET3
header; Board 1's LINE3 R/W wire and LINE4 RO wire land on J6 NET3a/NET3b. All on one
net, no extra jumper. Mode is chosen by patching: RO wire only = listen-only;
add the LINE3 R/W wire = drive/test. (Board 1's RO hardware can never drive.)

## Other Board 2 changes (2026-11-11)

- **SW1 / SW2** are now 4-pin screw terminals (12V_IN, 12V_OUT, 12V_OUT_LED, GND_LED) wired to off-board illuminated switches; 12V_OUT_LED is tied to 12V_OUT on the board (lamp lights when the output is live). SW1 = general power, SW2 = shared IGN for all J4 12V_IGN pins.
- **R2 / LED1 removed** (redundant — the switches have their own lamps).
- **D3 = 1.5KE24A TVS** (1500 W, 24 V, unidirectional, DO-27 axial; part on hand), fitted (no longer DNP): band to V12S, other end to GND. **Leads ~1.0 mm → 1.3 mm holes** (lead + 0.3 mm); on perfboard drill the holes out to 1.3 mm or solder the leads flat onto the pads.

## Per-module requirements

- **ECU:** C1033 black 18-way: 4 GND + 12V + 12V_IGN; C1017 red: K p23, L p20, immobiliser p26.
- **10AS:** GND + 12V_BAT + **12V_IGN (confirmed needed)** + immobiliser (C225 p15) + diagnostic K (C225 p17 = OBD pin 8, separate line).
- Future BCM/SRS etc.: build a new cable; PCB doesn't change.

## Open items

1. ~~Which RO net carries the 10AS diagnostic line~~ — RESOLVED 2026-11-11: NET2 and NET4 are interchangeable; pick either per session (listen-only for now).
2. J4: verify 43045-0412 suffix/pegs vs the Molex drawing; KiCad project started (`hardware/board2-pcb/`).
3. Update `gems-2pcb-schematic.html` Sheet 2 + part table; fix A1/A2... names in Board 1 docs.
4. Reconcile the three Board 2 designs.
5. `docs/board2-bench-hub.md` 10AS IGN note — corrected 2026-11-11 (naming there is still old K/L).

## Relationship to other Board 2 designs

Third independent design alongside `docs/two-board-rig.md` (16-pad + patch layer +
TB-ECU/TB-10AS) and `docs/board2-bench-hub.md` (generic TB-CAR panel). None chosen
as "the" design; don't assume this supersedes the others without the user saying so.
`hardware/j6-patch-bay/` (KiCad scaffold) shows the OLD layout and is stale.
