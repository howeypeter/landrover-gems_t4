# KiCad starter — 2-PCB build (CHECK BEFORE YOU TRUST IT)

> ⚠️ **These files were hand-authored and NOT opened or validated in KiCad.**
> Treat them as a **scaffold to check**, not a finished design. Verify every
> footprint name against your KiCad libraries and eyeball every net in the PCB
> editor's ratsnest before routing. The authoritative human-readable design is
> `../README.md` + the diagram `../../../diagrams/gems-2pcb-solution.html`.

## What these are

Two **KiCad netlists** (not schematics) — one per board:

- `gems-pcb1-main.net` — Pico + L9637D smart adapter
- `gems-pcb2-power.net` — DC input, protection, switches, ECU/adapter routing

A netlist is the most reliable thing to hand-author blind: no symbol graphics or
wire geometry to get wrong, just components + connections. You import it into the
**PCB editor**, which places all the footprints and shows the full ratsnest — a
real head start for layout, and every net is plain text you can check.

## How to use

1. KiCad → **New Project** (e.g. `gems-pcb1-main`).
2. Open the **PCB Editor** (Pcbnew).
3. **File ▸ Import ▸ Netlist…** → pick `gems-pcb1-main.net` → *Update PCB*.
   KiCad places the footprints and draws the ratsnest.
4. Fix any footprint it couldn't find (see the check table below), then **place**
   per the plan in `../README.md §2.4 / §3.4` and **route** to the trace-width /
   DRC targets in `../README.md §4`.
5. Repeat for `gems-pcb2-power.net`.
6. Export **Gerbers** + **CPL (pick-and-place)**; the assembly **BOM** (with the
   LCSC C-numbers) is already in `../pcb1-main-bom.csv` / `../pcb2-power-bom.csv`.

*(Prefer a schematic? Build one in Eeschema from `../README.md`'s netlist
sections — its symbols/values match these refs — then let KiCad regenerate the
netlist. That gives you ERC too.)*

## Footprint check table (the risky bit)

| Ref(s) | Footprint used | Check |
|---|---|---|
| U1 | `Package_SO:SOIC-8_3.9x4.9mm_P1.27mm` | standard — pads **1–8 = the L9637D pins** (1 RX, 2 LO, 3 VCC, 4 TX, 5 GND, 6 K, 7 VS, 8 LI) |
| **U2 (Pico)** | `RPi_Pico:RPi_Pico_SMD_TH` | **most likely to be missing** — install a Pico footprint lib or assign your own. Pads = **physical pin numbers** (GP0=1, GP1=2, GND=3 & 38, 3V3(OUT)=36). |
| R1/R2 | `Resistor_SMD:R_0805_2012Metric` | standard |
| C1/C2 | `Capacitor_SMD:C_0805_2012Metric` | standard |
| F1 | `Resistor_SMD:R_1206_3216Metric` | stand-in for a 1206 PPTC (DNP) |
| D1/D3 | `Diode_SMD:D_SMB` | TVS (DNP); **pad 1 = cathode** |
| D2 | `Diode_SMD:D_SMC` | SS54; **pad 1 = cathode** (band). Series: pad 2 (anode)=+12 in, pad 1 (cathode)=load |
| LED1 | `LED_SMD:LED_0805_2012Metric` | DNP; pad 1 = anode, pad 2 = cathode |
| JP1 | `PinHeader_1x02_P2.54mm_Vertical` | L↔K jumper (fit shunt) |
| J1/J3 | `PinHeader_1x04_P2.54mm_Vertical` | A=1 (+12), B=2 (GND), C=3 (K), D=4 (L) |
| J4 | `PinHeader_1x08_P2.54mm_Vertical` | 1=L, 2=K, 3=+12 main, 4=+12 ign, 5–8=GND |
| **J2, F2, SW1, SW2** | `PinHeader_1x02_P2.54mm_Vertical` | **placeholders** — the barrel jack, fuse holder and toggle switches are mechanical parts you pick; swap in your chosen part's real footprint (2 terminals each). |

## Don't-populate (DNP) for the bench

`F1`, `D1` (PCB1) and `LED1`, `R2`, `D3` (PCB2). The footprints are in the netlist
so the board has the pads, but leave them unpopulated for the first build (add the
Vs TVS `D1` + real fusing before the rig ever goes on a running vehicle). With
`F1` unpopulated, bridge its pads (or fit a 0 Ω) so +12 reaches Vs.

## Sanity checks to do once imported

- **JP1 fitted closed** ties `L_IN` to `K_NODE` (the 0xDA unlock). Confirm the
  ratsnest joins J1-D → JP1 → the K node.
- **12 V never touches the Pico** — `+12V`/`VS` only reach U1 pin 7 (via F1) and
  R1; the Pico is USB-powered. Verify no +12 net lands on any U2 pad.
- **Vcc is 3V3** — `VCC_3V3` joins U1-3, C1, and Pico pad 36 only.
- On PCB2, **V12S** feeds J3-A, J4-3 (ECU main) and SW2; **IGN_P8** is SW2→J4-4
  only. GND ties J2−, J3-B and J4 pins 5–8.
