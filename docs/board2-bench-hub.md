# Board 2 — bench hub (perfboard)

**Status: draft spec, not yet built.** Board 1 is perfboard (built); Board 2
follows the same build style — perfboard now, a fabbed PCB is a future option
once the design is proven. This doc is the wiring/terminal reference for that
perfboard build. See `docs/two-board-rig.md` for the narrative/rationale and
`diagrams/PCB_Board_Scheme/PCB_Board_Scheme.md` for Board 1's (fabbed) design,
which this board plugs into.

## What this board does

Board 2 is a **patch panel + power-distribution hub**, not a fixed harness.
It breaks Board 1's two K-line channels out to a generic terminal block;
**which car module each channel talks to is a per-session wiring choice**, not
a fixed design decision. This is a multi-use diagnostic tool — on any given
bench session you patch each channel to whichever module you're working with
(engine ECM, 10AS, ABS, SRS, or the immobiliser line directly), rather than
Board 2 hard-wiring "channel A = engine, channel B = 10AS" permanently.

There are no active parts (no transceivers, no pull-ups) on the signal lines —
those live on Board 1 (dual L9637D, U2/U3). Board 2 is pure pass-through
wiring plus the power section.

```
[Board 1 male OBD2 / direct wires] ──► [Board 2 patch panel] ──► whichever car module(s) you're testing
```

Board 1 is *either* in a car, *or* plugged into Board 2 — never both at once, so
OBD pin 16 only ever has one 12V origin.

## Terminal scheme — generic patch panel

Board 1 already exposes exactly this structure (two channels, each with a
driven line, a driven companion, and a read-only tap) — nothing changes on
Board 1. Board 2 just carries those same six signal terminals through to
wherever you patch them, plus the shared power/ground:

| Board 2 terminal | Board 1 terminal | Role |
|---|---|---|
| K1-A | A1 | Channel A driven line (R/W) |
| K1-B | A2 | Channel A driven companion (same node as K1-A) — e.g. asserting an L-line alongside K1 |
| K1-RO | A3 (LI1) | Channel A listen-only tap (R/O) |
| K2-A | B1 | Channel B driven line (R/W) |
| K2-B | B2 | Channel B driven companion (same node as K2-A) |
| K2-RO | B3 (LI2) | Channel B listen-only tap (R/O) |
| 12V-1 | — | unswitched power, paired with channel 1 (K1-A/B/RO)'s module |
| 12Vi-1 | — | switched via SW2 (shared ignition switch), channel 1's module |
| 12V-2 | — | unswitched power, paired with channel 2 (K2-A/B/RO)'s module |
| 12Vi-2 | — | switched via SW2 (same switch as 12Vi-1), channel 2's module |
| GND | — | star ground (shared) |

11 terminals total. Power is paired per channel (not one shared bus) —
separate main-power terminals per module — but the switched/ignition feed is
a **single shared switch (SW2)** driving both 12Vi-1 and 12Vi-2 together, not
two independent switches. Unlike a fixed harness, none of this table says
where a terminal "goes" — that depends on the session. The patch reference
below lists known destinations; which ones you actually wire up is decided
per test.

## Patch reference — known destinations

A signal lands on a Kx-A/B/RO terminal via whichever path reaches it: through
Board 1's male OBD2 plug + Board 2's female P2 socket for anything with a
J1962 pin, or as a **direct wire** (bypassing P2/OBD2 entirely) for the two
signals that have no J1962 pin at all.

| Module / signal | Reaches via | Notes |
|---|---|---|
| Engine ECM K-line | OBD pin 7 → ECU C1017 p23 | |
| Engine ECM L-line | OBD pin 15 → ECU C1017 p20 | drive alongside the engine K-line (same node, via -B) for 0xDA |
| 10AS K-line | OBD pin 8 → 10AS C225 p17 | |
| ABS K-line | shares OBD pin 7 with the engine on this vehicle (Discovery 1, per `docs/dlc-pinouts.md`) | verify per vehicle — some share pin 7, don't assume a dedicated ABS pin without checking |
| SRS/airbag K-line | OBD pin 13 on this vehicle | some vehicles use pin 13/14 differently (e.g. P38) — meter-verify per vehicle before patching |
| Immobiliser / mobilise line | **direct wire**, no OBD2 pin — 10AS C225 p15 ↔ ECU C1017 p26 | patch onto a -A terminal to actively drive/read it (see "Example 1" below); do this only when that channel isn't also carrying a module's real K-line |
| MIL-shared line | **direct wire**, no OBD2 pin — 10AS C225 p11 ↔ ECU C1032 p22 | safest on a -RO terminal (passive view, zero drive-conflict risk); flagged "verify" in `docs/10as-pinout.md` |

**This project's verified pinout is left as-is** (no changes made here) —
the Discovery 1 mapping in `docs/dlc-pinouts.md` is the source of truth for
*this* vehicle. If you patch this board onto a different GEMS-era vehicle
(e.g. a P38), meter-verify that vehicle's own pin assignments before wiring;
don't assume the Disco-1 table carries over.

## Example configurations

**Example 1 — immobiliser control/view:**
```
K1-A  →  ECU C1017 p23 (engine K-line)
K1-B  →  ECU C1017 p20 (L-line, driven with K1)
K1-RO →  (unused, or passively tap OBD pin 8 to watch the 10AS K-line without driving it)
K2-A  →  ECU C1017 p26 (immobiliser/mobilise — actively drive or read it)
K2-B  →  (not used)
K2-RO →  (not used)

12V-1 / 12Vi-1  →  ECU C1033 p7 / p8 (main / ignition, pending meter-verify)
12V-2 / 12Vi-2  →  (not used — no 10AS K-line patched in this example)
```

**Example 2 — default ECU + 10AS diagnostics (the original design):**
```
K1-A  →  ECU C1017 p23 (engine K-line)
K1-B  →  ECU C1017 p20 (L-line, driven with K1)
K1-RO →  (not used)
K2-A  →  10AS C225 p17 (10AS K-line)
K2-B  →  (not used)
K2-RO →  MIL: 10AS C225 p11 ↔ ECU C1032 p22 (passive view only)

12V-1 / 12Vi-1  →  ECU C1033 p7 / p8 (main / ignition, pending meter-verify)
12V-2 / 12Vi-2  →  10AS C225 p10, p25 (both unswitched on the car — 12Vi-2
                    left unused unless you want to test the 10AS under a
                    simulated switched feed; SW2 gates both 12Vi outputs
                    together, so switching it also affects 12Vi-1/ECU)
```

These are two configurations of the same hardware — moving wires between
sessions, not two different boards. Don't run Example 1 and Example 2
simultaneously on K2; driving the immobiliser line and the 10AS's real
K-line on the same channel at once is a drive conflict (see the patch
reference note above).

## Power path

| Ref | Part | Notes |
|---|---|---|
| J2 | DC barrel jack (2.1mm) | bench 12V in, low-amp supply |
| D2 | Schottky (**1N5817**, 1A/20V) | reverse-polarity protection on the DC input — rated at the fuse's level, standard for a low-duty-cycle bench setup; watch for warm-to-the-touch during early testing in case F2 is slow-blow |
| F2 | **1A** fuse + holder | main bench fuse (single fuse, not per-branch — bench supply is current-limited, so per-branch fusing isn't worth the parts); starting conservative, raise if the ECU's actual draw needs it |
| SW1 | 12mm illuminated latching pushbutton, 12V/5A (DaierTek-style, 4-wire: red/black=LED, 2×green=contacts) | master 12V — gates the whole rail; built-in LED replaces a separate PWR indicator (own 510Ω resistor added in series regardless — safe default whether or not the switch has an internal one) |
| SW2 | 12mm illuminated latching pushbutton, 12V/5A (same part as SW1) | shared switched feed — gates **both** 12Vi-1 and 12Vi-2 together (e.g. ECU ignition C1033 p8 — pending meter-verify); built-in LED replaces a separate IGN indicator |

```
J2 (+12V in) ── D2 (rev-pol) ── F2 (1A) ── SW1 ── 12V rail

12V rail ── Board 1 feed (OBD pin 16)
12V rail ── 12V-1 (channel 1's main power, patched per session)
12V rail ── 12V-2 (channel 2's main power, patched per session)
12V rail ── SW2 ── 12Vi-1 AND 12Vi-2 (shared switched feed, both channels at once)
```

**Power-pin caveat:** `docs/gems-ecu-pinout.md` labels C1033 p7 "MFI Load
Relay" and p8 "Satellite Fuse Box 1" — not plainly "main 12V" / "ignition". An
earlier bench note assumed the opposite (p7 = main, p8 = ignition). **Meter
both, unpowered, before applying 12V.** Don't hard-code which one gets SW2
until confirmed.

**Brownout note:** the bench supply is low-amperage with little headroom. A
relay coil energizing (fuel pump, MIL) or ECU crank could sag the rail, which
would also shift Board 1's K-line pull-up reference voltage. A bulk capacitor
(470–1000 µF, 25V) after SW1 is recommended to smooth this — not yet added to
the BOM below; add before first power-up if nuisance resets or K-line glitches
show up.

**Ground:** one star point. DC-adapter GND, both OBD grounds, ECU GND, 10AS
GND, and Pico USB GND (if used) all return to this single point — avoids
ground loops between the boxes.

**Combining multiple grounds (e.g. 4 ECU + 1 10AS) onto the GND terminal:**
since this is perfboard, the simplest approach is a soldered ground bus — a
row of pads bridged with bare bus wire, with all incoming ground wires landing
on that row and one wire out to the single GND terminal / star point. No extra
parts needed, and trivially rated for the sub-1A currents here. (A car-audio-
style ground distribution block, or a barrier strip with a jumper comb, would
also work if a discrete/serviceable part is preferred over bare perfboard
pads — not needed at this current level.)

## BOM (perfboard build)

| Ref | Part | Notes |
|---|---|---|
| P2 | Female J1962 pigtail | receives Board 1's male plug; wired to TB-CAR, no OBD housing on the board itself |
| J2 | DC barrel jack, 2.1mm | bench 12V in |
| D2 | Schottky, 1N5817 (1A/20V) | reverse-polarity protection, matched to F2 |
| F2 | 1A fuse + holder | main bench fuse |
| SW1 | 12mm illuminated latching pushbutton, 12V/5A, pre-wired (red/black=LED, 2×green=contacts) | master power + built-in PWR indicator in one panel hole |
| SW2 | same part as SW1 | shared switched feed + built-in IGN indicator in one panel hole |
| — | 2× 510Ω resistor | in series with each switch's red/black LED leads — safe default regardless of whether the switch has its own internal resistor |
| TB-CAR | screw terminal block, 11 positions | K1-A, K1-B, K1-RO, K2-A, K2-B, K2-RO, 12V-1, 12Vi-1, 12V-2, 12Vi-2, GND — see terminal scheme above |
| — | perfboard, 0.1" pitch | one board |
| — | 22 AWG hookup wire | +12V / power runs should stay comfortable for a couple of amps |
| — | patch wires | short jumpers used to wire each session's configuration onto TB-CAR; not a fixed BOM item, made/changed as needed |

Optional, not yet added: bulk capacitor (see brownout note above).

**Signals with no J1962 pin** (immobiliser/mobilise, MIL-shared) reach TB-CAR
as direct wires rather than through P2 — there's no standard OBD2 pin to
carry them.

## Pre-power checklist

1. **Meter C1033 p7 and p8** (ECU, unpowered) to confirm which is main 12V and
   which is switched/ignition before wiring SW2 to either.
2. **Meter continuity** between the ECU's ground-distribution pins if you ever
   want to trim grounds — not needed today, all are wired to the bus.
3. Confirm the MIL-shared link (10AS p11 → ECU C1032 p22) with a meter before
   relying on it — flagged "verify" in `docs/10as-pinout.md`.
4. Before patching a new vehicle's module onto K1/K2 (ABS, SRS, etc.), verify
   that vehicle's own pin assignments — don't assume the Disco-1 table applies
   (see the patch reference caveat above).
5. First contact on any new configuration: read-only
   (`gems_t4 kline live` / `secure --immo`) before any write.
6. Confirm single 12V source rule: Board 1 is in a car OR in Board 2, never
   both — don't power the bench DC jack while Board 1 is also plugged into a
   vehicle.
7. Never patch a channel to drive two different modules' K-lines at once (see
   "Example configurations" above) — it's a drive conflict, not a supported
   mode.
8. L9637D pin-1 orientation and Vcc=3.3V were already checked on Board 1; no
   action needed on Board 2 (no transceivers here).

## Open / deferred

- Exact bench-supply current rating is TBD — started at a conservative **1A**
  fuse (with a matched 1N5817 diode); raise both together if the ECU's actual
  bench current draw needs more headroom once measured.
- EKA input pins (10AS C225 p7/p8) — not wired, add later if the EKA bench
  test is picked up.
- Bulk capacitor for brownout smoothing — recommended, not yet in the BOM.
- Reconciling the Disco-1 vs P38 (or other GEMS-era vehicle) pin differences
  into one reference table — left as separate per-vehicle notes for now, not
  merged.
- A fabbed PCB version of this board, mirroring Board 1's flux.ai-authored
  design — future option once the perfboard build is proven.
