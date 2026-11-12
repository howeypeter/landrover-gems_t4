# Board 1 — Minimum Viable Product (MVP)

This is the original, minimal design concept — before today's flux.ai
schematic-capture process (automotive-grade parts chase, reverse-polarity
protection stage, JLCPCB sourcing analysis, terminal-block splitting into
J1/J2/J3, test points, etc.). It's a standalone reference, not tied to the
flux project or the chunked process documented elsewhere in this folder.

**Goal**: the simplest board that still runs off real vehicle 12V power
with basic fuse protection — no TVS clamp, no buck regulator, no
reverse-polarity protection stage. If you ever want to strip the full
design back down to basics, this is that baseline.

## What it does

A Raspberry Pi Pico drives two independent ST L9637D K-line transceivers,
each wired to its own terminal block pins — e.g. one channel to the engine
ECU, the other to a body/alarm module — without contention, since each
channel is fully separate (own transceiver, own pull-up, own UART).

The transceivers' Vs (battery) pins are fed from the vehicle's 12V through
a single fuse — no TVS surge clamp, no buck regulator, no reverse-polarity
protection. The Pico itself is still powered over USB. This is intentionally
the bare-minimum version that's still usable on a real car, not the fully
hardened one.

## BOM

| Ref | Part | Value / Spec | Notes |
|---|---|---|---|
| U1 | Raspberry Pi Pico | RP2040 (or Pico 2 / Pico W — any variant) | Host MCU, powered via USB |
| U2 | ST L9637D | SOIC-8 (or DIP-8 breakout for breadboard) | K-line transceiver, channel 1 |
| U3 | ST L9637D | SOIC-8 (or DIP-8 breakout for breadboard) | K-line transceiver, channel 2 |
| R1 | Resistor | 510 Ω | K-line pull-up, channel 1 (K↔Vs) |
| R2 | Resistor | 510 Ω | K-line pull-up, channel 2 (K↔Vs) |
| C1 | Ceramic cap | 100 nF | Vcc decoupling, channel 1, close to U2 |
| C2 | Ceramic cap | 100 nF | Vcc decoupling, channel 2, close to U3 |
| F1 | Fuse | 1 A (inline) | Protects the 12V feed to both transceivers' Vs pins |
| J1 | 9-position terminal block | screw terminals, header, or direct wire | See terminal scheme below |

That's it — 9 components total.

## Terminal block (9 positions: A1, A2, A3, B1, B2, B3, 12V, GND, GND)

Single row, same physical order as the full board's terminal scheme:

```
[ A1 ][ A2 ][ A3 ]   [ B1 ][ B2 ][ B3 ]   [ 12V ]   [ GND ][ GND ]
```

| Terminal | Net | Connects to | Typical OBD2 pin |
|---|---|---|---|
| A1 | K1 | U2 pin 6 (K) | 7 — engine/ABS K-line |
| A2 | K1 (same node as A1) | U2 pin 6 (K) | 15 — L-line, tie here to keep the K+L strap open if wanted |
| A3 | LI1 | U2 pin 8 (LI) | (spare / optional listen tap) |
| B1 | K2 | U3 pin 6 (K) | 8 — 10AS/body-module K-line |
| B2 | K2 (same node as B1) | U3 pin 6 (K) | (spare) |
| B3 | LI2 | U3 pin 8 (LI) | (spare / optional listen tap) |
| 12V | 12V_IN | F1 → U2 pin 7 (Vs), U3 pin 7 (Vs) | 16 — vehicle battery feed |
| GND | GND | common ground | 4 — chassis ground |
| GND | GND | common ground | 5 — signal ground |

A1/A2 and B1/B2 are each a single electrical node with two physical screw
positions — handy for landing two wires (e.g. K + L) on the same net
without extra hardware. A3/B3 (LI) are separate, read-only listen taps —
the L9637D can sense a signal there but never drive it.

## Wiring per L9637D (applies to both U2 and U3)

Standard L9637D pinout (SOIC-8 / DIP-8):

| Pin | Name | Connects to | Direction |
|---|---|---|---|
| 1 | RX | Pico GPIO (input) | chip → Pico: reflects K-line state |
| 2 | LO | Pico GPIO (input) | chip → Pico: L-line comparator result (if using LI) |
| 3 | VCC | Pico 3V3 | power in |
| 4 | TX | Pico GPIO (output) | Pico → chip: drives K-line |
| 5 | GND | common ground | power in |
| 6 | K | Terminal A1/A2 (U2) or B1/B2 (U3) | bidirectional bus |
| 7 | Vs | Fused 12V (via F1) | power in |
| 8 | LI | Terminal A3 (U2) or B3 (U3) | input, read-only |

R1 bridges U2 pins 6–7 (K to Vs pull-up). R2 bridges U3 pins 6–7. C1 bridges
U2 pins 3–5 (Vcc decoupling), mounted close to the chip. C2 does the same
for U3.

## Power path

```
Terminal 12V → F1 (1A fuse) → U2 pin 7 (Vs), U3 pin 7 (Vs)
Terminal GND ×2 → common ground → U2 pin 5, U3 pin 5, Pico GND
Pico 3V3 → U2 pin 3 (VCC), U3 pin 3 (VCC)
Pico powered separately via USB
```

F1 is the only protection on the 12V feed — no TVS clamp for transient
spikes, no reverse-polarity protection if the 12V/GND terminals get wired
backwards. That's the tradeoff for keeping this to 9 components.

## Pico connections

| Pico pin | Connects to |
|---|---|
| 3V3 | U2 VCC, U3 VCC |
| GND | common ground, U2 GND, U3 GND |
| GPIO0 | U2 TX |
| GPIO1 | U2 RX |
| GPIO2 | U2 LO |
| GPIO4 | U3 TX |
| GPIO5 | U3 RX |
| GPIO6 | U3 LO |

(GPIO numbers here follow the same allocation used in the full board —
GP0/GP1 = UART0 for channel 1, GP4/GP5 = UART1 for channel 2 — but any
free GPIO pair with UART capability works if you're breadboarding this
differently.)

## What this MVP deliberately leaves out

Compared to the fully-worked board built via flux.ai today:

- **No TVS clamp** (no D1) — a voltage spike/transient on the 12V feed
  isn't clamped, just fused.
- **No buck regulator or reverse-polarity protection** (no REG1, no L1, no
  D4/Q1 stage, no output capacitors) — the Pico stays USB-powered rather
  than running self-contained off vehicle 12V.
- **No connector splitting** — one 9-position block, not three separate
  J1/J2/J3 connectors.
- **No automotive-qualified parts** — any standard-grade L9637D, resistor,
  capacitor, and fuse works.
- **No test points, no silkscreen labeling, no JLCPCB sourcing analysis.**
- **No footprint/manufacturing concerns** — this is a breadboard/perfboard-
  friendly minimal spec, not something laid out for PCB fabrication.

If/when you want the board to run fully self-powered off the OBD 12V rail
(no USB needed) or to survive a genuine voltage transient/reverse-polarity
miswiring, that's the point where you'd reach for the TVS/buck/reverse-
polarity additions — those aren't wasted work, they solve real problems
this MVP doesn't take on.
