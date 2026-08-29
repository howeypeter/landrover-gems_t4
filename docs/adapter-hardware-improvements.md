# Adapter hardware — improvements & hardening notes

Notes on the Pico + **L9637D** K-line adapter beyond the minimum "make it talk"
wiring. The core adapter (Pico + L9637D + one 510 Ω resistor) is enough for
**bench** bring-up off a clean PC/ATX PSU; the items below harden it and — one
of them especially — are what you add **before moving from the bench to a
running vehicle**.

Sourced from an adversarial review against the **ST L9637D datasheet, Doc ID
1765 Rev 7** (local copy: `C:\Users\howey\Downloads\E-L9637D.PDF`). Companion
wiring diagrams: `diagrams/gems-adapter-wiring.html` (on-car / OBD) and
`diagrams/gems-bench-rig-wiring.html` (bench PSU rig).

## L9637D pinout (SO-8) — for reference

| Pin | Name | Function |
|----:|------|----------|
| 1 | RX | Received data out → Pico GP1 (idles at Vcc) |
| 2 | LO | L-line comparator output (unused) |
| 3 | VCC | Logic supply — **3.3 V from the Pico, never 5 V** |
| 4 | TX | Transmit data in ← Pico GP0 |
| 5 | GND | Ground |
| 6 | K | Bidirectional K-line I/O → ECU K-line |
| 7 | VS | Battery / +12 V supply (4.5–36 V) |
| 8 | LI | L-line comparator input (unused) |

## What's required vs. recommended vs. before-car

### Required (bench and car)
- **510 Ω pull-up, pin 6 (K) → pin 7 (Vs).** The K-line is open-drain; this is
  what holds it high. Datasheet's own characterization value; max is
  **R_KO ≤ 5 kΩ**. The ECU K-line wire lands on the *same* pin 6 — so pin 6
  carries both the pull-up and the bus wire. That is correct, not a fault.
- **Vcc (pin 3) = 3.3 V, taken from the Pico — never 5 V.** RX (pin 1) idles at
  Vcc; at 5 V it would push 5 V into the Pico's non-5 V-tolerant GP1 and can
  destroy it. Vcc abs-max is 7 V; operating range 3–5 V (3.3 V is in spec).

### Recommended (optional — skip for first bench comms, add later)
- **100 nF (0.1 µF) decoupling cap, pin 3 (Vcc) → GND (pin 5),** mounted close to
  the chip. Steadies the logic supply. Ceramic, no polarity, marked "104".
- **C_K cap on the K line: ~1 nF, pin 6 (K) → GND, and it must be ≤ 1.3 nF.**
  Suppresses line spikes / shapes the output slope for EMI (the datasheet's AC
  specs assume C_K ≤ 1.3 nF). Do not exceed 1.3 nF.

### Before it goes in a running vehicle (NOT needed on the bench PSU)
- **Vs transient clamp (TVS) on pin 7.** A running Land Rover's 12 V rail throws
  load-dump / inductive spikes that can exceed the L9637D's limits (Vs abs-max
  36 V DC, 40 V for 400 ms). A transient above ~40 V destroys the chip. Fit a
  TVS/clamp on Vs (standoff ~24–33 V, clamping below 40 V), ideally with a small
  series element. **On a bench PC/ATX PSU this is a non-issue** — that 12 V is
  clean and regulated with no alternator spikes — so it's a pre-car step, not a
  bench step.
- **Inline fuse (1–2 A) on the +12 V feed.** Standard for anything tapping
  vehicle 12 V (OBD pin 16 is battery-live even key-off). Cheap short protection.

## The failure that actually kills boards: chip orientation

The 12 V must land **only** on pin 7 (Vs). Pins 1–4 and 8 live in the low-voltage
(≤ 7 V) domain — putting 12 V on any of them (a flipped SO-8, or an off-by-one on
the breakout) exceeds abs-max and destroys the chip and possibly the Pico.
Before applying power: **find the pin-1 notch/dot** (Figure 2 is a top view;
numbering runs counter-clockwise from pin 1) and confirm pin 7 is where you
think it is. This is the single easiest way to fry the adapter.

## Things that are already correct (don't "fix" them)

- **No series resistor on the K line.** The K pin drives the bus directly — it's
  internally current-limited (I_KSC ~60 mA typ), short-protected to GND/Vs, and
  rated −24 V…Vs. The datasheet application circuit shows no K series resistor.
- **Parallel pull-up with the ECU.** A real GEMS ECU already pulls K up to
  battery internally; your 510 Ω sits in parallel with it. Combined low-drive
  current is a bit higher but well within the L9637D's K current limit — fine,
  just be aware the bus is loaded a little more than 510 Ω alone.
- **Reverse-battery** on Vs is internally survivable to −24 V. It's *positive*
  transients (load dump) that are the killer and are not internally clamped —
  hence the external TVS above.

## Added bill of materials (beyond the base adapter)

| Part | Value | Where | When |
|------|-------|-------|------|
| Resistor | 510 Ω (≤ 5 kΩ) | pin 6 (K) → pin 7 (Vs) | required |
| Cap (ceramic) | 100 nF / 0.1 µF | pin 3 (Vcc) → GND | recommended |
| Cap (ceramic) | ~1 nF (≤ 1.3 nF) | pin 6 (K) → GND | recommended |
| TVS / transient suppressor | ~24–33 V standoff | pin 7 (Vs) → GND | before in-car |
| Fuse | 1–2 A inline | +12 V feed | before in-car |

## Bench-first workflow (unchanged, restated)

1. Wire the base adapter + the 510 Ω pull-up. Vcc from 3V3.
2. Triple-check pin-1 orientation before any power.
3. Power from a clean PC/ATX PSU (green→black jumper to switch it on). No TVS
   needed at this stage.
4. First contact is **read-only**: prove writes on the virtual ECU first
   (`gems_t4 immo status`, `coding read`), then read the car
   (`gems_t4 live --port COMx`).
5. Only after adding the Vs transient clamp + fuse should the adapter go onto a
   running vehicle's live 12 V.
