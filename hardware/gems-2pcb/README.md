# GEMS bench rig — 2-PCB JLCPCB design package

Manufacturing package for the two-box GEMS bench tool. Companion to the pin-exact
schematic at [`diagrams/gems-2pcb-solution.html`](../../diagrams/gems-2pcb-solution.html)
and the manual §11 "Two-box build". This doc has everything needed to route the
boards in KiCad/EasyEDA and order them from **JLCPCB** (jlcpcb.com) with SMD
assembly — *except* the final Gerbers, which come out of the layout tool.

- **PCB1 — MAIN:** Pico + L9637D smart adapter.
- **PCB2 — POWER:** DC input, protection, PWR/IGN switches, ECU + adapter routing.

**Assembly model (chosen):** JLCPCB assembles the **SMD** parts (top side only);
you **hand-solder** the through-hole connectors, switches, barrel jack, jumper
header and the Pico module. This is the cheapest/simplest split and keeps the
PCBA BOM tiny.

> ⚠️ **LCSC part numbers below are `VERIFY` placeholders.** LCSC stock/pricing
> changes daily and a wrong part # in a JLC BOM mis-populates the board. Each line
> gives the exact spec + a search string; confirm the real part # (and *Basic* vs
> *Extended*) on the JLCPCB parts search before ordering. Ask and I'll look them
> up live to fill these in.

---

## 1 · JLCPCB fab settings (both boards)

| Setting | Value | Note |
|---|---|---|
| Layers | **2** | plenty for this |
| Dimensions | PCB1 ≈ 55 × 75 mm · PCB2 ≈ 65 × 85 mm | final size from layout; leave room for the Pico + panel switches |
| Thickness | 1.6 mm | standard |
| Copper weight | 1 oz (35 µm) | fine with the wide power traces below |
| Surface finish | HASL (lead-free) | SO-8 is 1.27 mm pitch — no need for ENIG |
| Min track/space | 0.20 mm design target | JLC does 0.127 mm; we don't need it |
| Min via | 0.3 mm drill / 0.6 mm pad | standard |
| Solder mask / silk | any | put ref-des + pin-1 marks on silk |
| Impedance control | **No** | 10.4 kbit/s — irrelevant |

**PCBA options:** Assembly = **Economic**, **top side only**, standard tooling.
Prefer **Basic** parts (no per-type feeder fee); each **Extended** part adds a
one-off ~US$3 loading fee.

---

## 2 · PCB1 — MAIN

### 2.1 SMD parts — JLCPCB assembles (see `pcb1-main-bom.csv`)

| Ref | Value | Footprint | Basic? | Notes |
|---|---|---|---|---|
| U1 | **ST L9637D** (E-L9637D013TR) | SOIC-8 (1.27 mm) | Extended | K-line transceiver — **confirmed in stock** as `E-L9637D013TR` (SO-8 T&R); grab its LCSC C-number. Specialty IC, so almost certainly Extended (~$3 feeder, fine for one part). |
| R1 | 510 Ω ±1 % 1/8 W | R0805 | Basic | K→Vs pull-up (required) |
| C1 | 0.1 µF X7R 50 V | C0805 | Basic | Vcc decoupling |
| C2 | 1 nF C0G/X7R 50 V | C0805 | Basic | K-line cap (≤1.3 nF); optional — can DNP for first build |
| F1 | PPTC 0.5 A hold | 1206 | Basic | Vs-branch fuse; optional (PCB2 has the main fuse) — DNP ok |
| D1 | TVS 24 V standoff | SMB (DO-214AA) | Extended | Vs clamp; **before-car only** — DNP for the bench |

### 2.2 Through-hole — you hand-solder (NOT in the PCBA BOM)

| Ref | Part | Footprint |
|---|---|---|
| U2 | Raspberry Pi Pico / Pico 2 | 2× 20-pin, 2.54 mm (castellated or header) |
| J1 | Molex Micro-Fit 3.0, 4-circuit | vertical or right-angle THT |
| JP1 | 2-pin header 2.54 mm + shunt | fit **closed** (L↔K tie) |

### 2.3 Netlist (route to this)

```
+12V (J1.A) ── F1 ── U1.7 (Vs)
U1.7 (Vs) ── R1 510Ω ── U1.6 (K)          [K node]
U1.6 (K)  ── J1.C  (K to ECU)
U1.6 (K)  ── C2 1nF ── GND                (optional)
J1.D (L)  ── JP1 ── U1.6 (K node)         [L tie, fitted closed]
U1.3 (Vcc) ── Pico 3V3 (phys pin 36) ;  C1 0.1µF U1.3→GND
U1.4 (TX) ── Pico GP0    ;   U1.1 (RX) ── Pico GP1
U1.8 (LI) ── GND         ;   U1.2 (LO) ── (no connect)
GND net: U1.5 + Pico GND + J1.B          [star ground]
D1 (TVS) U1.7 → GND       (DNP for bench)
Pico USB ── laptop (power + data)         [12V never touches the Pico]
```

### 2.4 Placement / routing

- Pico footprint along one edge (USB at the board edge). L9637D next to the Pico's
  GP0/GP1/3V3/GND pins to keep TX/RX/Vcc short.
- **K node compact:** U1 pin 6, R1, C2 and the J1-C pad clustered; short traces.
- R1 sits directly between U1 pin 7 (Vs) and pin 6 (K).
- C1 across U1 pin 3↔5, as close to the chip as possible.
- J1 Molex at the opposite edge from USB. Keep the +12 V (J1.A→F1→Vs) trace away
  from the RX/TX pair.
- **Star ground**; a ground pour on the bottom layer is easiest.

---

## 3 · PCB2 — POWER / ROUTING

### 3.1 SMD parts — JLCPCB assembles (see `pcb2-power-bom.csv`)

| Ref | Value | Footprint | Basic? | Notes |
|---|---|---|---|---|
| D2 | Schottky 5 A 40 V (e.g. SS54) | SMC (DO-214AB) | Basic | series reverse-polarity protect (simple, ~0.5 V drop). *Alt: low-drop P-FET — see 3.4.* |
| D3 | TVS 24 V (SMBJ24A) | SMB | Extended | 12 V clamp; optional — DNP for bench |
| LED1 | power indicator | LED0805 | Basic | optional |
| R2 | 2.2 kΩ 1/8 W | R0805 | Basic | LED series (optional) |

*(PCB2 is mostly connectors/switches; its SMD content is deliberately tiny. If you
prefer, order PCB2 as a **bare board** and hand-solder D2 too — your call.)*

### 3.2 Through-hole — you hand-solder (NOT in the PCBA BOM)

| Ref | Part | Footprint |
|---|---|---|
| J2 | DC barrel jack 2.1 mm (or 2-pos terminal) | THT |
| F2 | Fuse holder + 3–5 A blade fuse | THT (or use an SMD PPTC — see 3.4) |
| SW1 | Toggle SPST, 12 V ≥5 A (general PWR) | panel |
| SW2 | Toggle SPST, 12 V ≥3 A (IGN) | panel |
| J3 | Molex Micro-Fit 3.0, 4-circuit (→ PCB1) | THT |
| J4 | Molex Micro-Fit 3.0, 8-circuit (→ ECU) | THT |

### 3.3 Netlist (route to this)

```
J2 (+12 in) ── D2 (rev-pol) ── F2 (main fuse) ── SW1 ── V12S rail
V12S ── J3.A            (+12 to PCB1 / L9637D Vs)
V12S ── J4-3            (ECU C1033 pin 7, main power)
V12S ── SW2 ── J4-4     (ECU C1033 pin 8, ignition)
GND (J2 −) ── J3.B, J4-5, J4-6, J4-7, J4-8   (ECU pins 5/9/10/16)
J3.C (K) ── J4-2   (ECU C1017 pin 23, K pass-through)
J3.D (L) ── J4-1   (ECU C1017 pin 20, L pass-through)
D3 (TVS) V12S→GND (DNP for bench) ;  LED1+R2 V12S→GND (optional)
```

**8-pin Molex (J4) pin map:** 1=L, 2=K, 3=+12 main(p7), 4=+12 ign(p8),
5–8 = GND (ECU p5/p9/p10/p16). **4-pin Molex (J1/J3):** A=+12, B=GND, C=K, D=L.

### 3.4 Placement / routing

- J2 → D2 → F2 → SW1 in a line at the input edge. **V12S as a copper pour/fat
  trace** (≥1.5 mm) feeding J3.A, J4-3 and SW2.
- SW2 between V12S and J4-4 only.
- Big **ground pour**; tie J2−, J3.B and J4-5..8 to it.
- K/L are just two pass-through traces J3.C↔J4-2 and J3.D↔J4-1 (≥0.3 mm).
- Switches at the box's front edge; Molex at the rear.
- **Reverse-polarity choice:** the Schottky (D2) is one Basic part and dead
  simple (~0.5 V drop → ECU sees ~11.5 V, fine on a bench). For near-zero drop use
  a P-FET high-side (source→load, drain→input, gate→GND via ~10 kΩ + a 10–15 V
  zener gate clamp) rated ≥5 A — more parts, verify LCSC. Schottky recommended.
- **Fuse choice:** a THT blade holder (F2) is robust and obvious; an SMD PPTC
  (~3 A hold, 1812) is JLC-placeable but resettable-only and trips ~2× hold.

---

## 4 · Trace-width / DRC targets

| Net class | Min width | Why |
|---|---|---|
| +12 V / V12S / ECU power | **1.5 mm** (or pour) | a few A with relays; 1 oz copper |
| GND | pour | star/plane |
| K / L | 0.4 mm | signal, but keep robust |
| TX / RX / Vcc (PCB1) | 0.3 mm | logic |
| Clearance | 0.2 mm min | JLC easily meets this |

---

## 5 · Order workflow (JLCPCB)

1. **Route** each board in KiCad or EasyEDA from the netlists above → export
   **Gerbers**, plus **BOM.csv** and **CPL.csv** (pick-and-place) for the SMD parts.
   (The CSVs here are the BOM starting point; CPL coordinates come from the layout.)
2. **Fab:** upload the Gerbers per board; set the fab options from §1.
3. **Assembly:** enable PCBA (Economic, top side); upload BOM + CPL; in JLC's
   review, confirm each part maps to an in-stock LCSC # and watch the
   Basic/Extended split (swap Extended → Basic where a jellybean equivalent
   exists).
4. **Hand-solder** the through-hole lists (§2.2, §3.2) when the boards arrive:
   Pico, Molex, switches, jack, JP1 header (fit the shunt), fuse holder.
5. **Bring-up** per the manual: verify **L9637D pin-1 orientation** and **Vcc =
   3.3 V** *before* power; first contact read-only (`gems_t4 kline live --port COMx`).

---

## 6 · Part-sourcing checklist (verify on LCSC/JLCPCB)

- [x] **U1 L9637D** — **in stock as `E-L9637D013TR`** (SO-8 T&R). Grab its LCSC
  C-number; expect Extended (~$3 one-off feeder fee — fine for a single IC).
- [ ] R1 510 Ω 0805, C1 0.1 µF 0805, C2 1 nF 0805, R2 2.2 kΩ 0805 — pick the
  **Basic** parts (zero feeder fee).
- [ ] D2 Schottky 5 A (SS54 or equiv), SMC.
- [ ] Molex Micro-Fit 3.0 4- and 8-circuit (J1/J3/J4) + crimp terminals + mating
  housings for the cables.
- [ ] Toggle switches (SW1/SW2), barrel jack (J2), fuse holder + fuse (F2).
- [ ] Optional/DNP for the bench: D1, D3, F1, LED1 — add the Vs TVS (D1) + real
  fusing before the rig ever goes on a running vehicle.

Bring-up, safety and the confirmed pinout live in the manual (§10–11, §15) and
`memory/real-gems-protocol.md`. JP1 (L↔K) reflects the 2026-09-04 finding that the
`0xDA` manufacturer channel opens only with the L-line tied to K.
