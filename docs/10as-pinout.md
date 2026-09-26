# Lucas 10AS / Theft Alarm Unit (Z163) — pinout & bench wiring

**Source:** RAVE electrical troubleshooting manual `etlj970x.pdf` (1997 NAS
Discovery 1), section **T2 "THEFT ALARM SYSTEM (NAS)"**, pages 322–336. This is
the authoritative circuit for the user's exact truck. RAVE labels the Lucas 10AS
the **"Theft Alarm Unit (Z163)"**; it has two connectors, **C225** (multiway) and
**C274**.

## Bench unit (this project's physical 10AS)

Photographed 2026-09-25. Confirmed the **full 10AS alarm/immobiliser ECU** (NOT a
standalone fob receiver — it has both connectors below, and the RF receiver is
*integrated*, which is why it carries an FCC ID):

| Label | Value |
|---|---|
| Land Rover P/N | **AMR 6428** |
| System / freq | **10AS-315 MHz** → **NAS** (North America; ROW = 433 MHz) |
| Lucas P/N | 52010377A |
| Serial | 1095784 |
| Build date | **wk 39 / 1996** |
| Receiver | Lucas **5RXA**, FCC ID **KHH5RXA** (integrated 315 MHz fob RX) |

**Connector ↔ RAVE mapping (this unit):**

| Physical connector | RAVE name | Pins | Role |
|---|---|---|---|
| **Grey** | **C225** | ~26-way | K-line, mobilise, power, antenna, switch inputs |
| **Green** | **C274** | ~12-way | ground, 30 A lock feed, indicators, horn, LED |

⚠️ **NOT from the same truck as the bench GEMS ECM** (user, 2026-09-25) — so
auto-pair won't work; mobilising the ECM with this 10AS needs **Security-Learn**
(`A300622588`). See "Pairing the ECM to the 10AS" below.

⚠️ **Verify physical pin numbering** on the grey 26-way before clipping in — find
the moulded pin-1 marker and row order; RAVE gives logical pin numbers, not the
cavity map.

> ⚠️ **Bench context.** This is for wiring the 10AS **directly to the bench**, not
> through the OBD-II socket. Pin numbers below are the **10AS unit-connector** pins
> (what you clip to on the bench). Where the car routes a wire to the OBD socket it
> is noted only for reference.

> ⚠️ **Two verification caveats.** (1) RAVE gives *logical* pin numbers, not the
> physical connector-cavity map — confirm the cavity positions on the real plug
> before clipping in. (2) The 10AS speaks a **proprietary Lucas protocol at its own
> address** (not GEMS 0xDA, not OBD Mode 09); powering it and reaching its K-line
> is electrical step one — the addressing/commands to read the EKA are still
> unmapped and need bench probing.

## Physical connector layout (cavity map)

From a community "10AS Central Locking Connections" graphic (added 2026-09-25;
kept local at `docs/img/10as-central-locking-connections.png`, gitignored as
third-party like the RAVE PDFs). This resolves the pin-numbering caveat — it's the
**connector-face view** (looking into the terminal side), and it **corroborates
RAVE**: the graphic draws C225 pin 7 yellow (= RAVE `YK`), C274 pin 2 orange
(= `O`), C274 pin 3 pink (= `K`) — the drawing colours ARE the LR wire colours.

```
GREY connector = C225 (26-way), connector face:
  top row:    13 12 11 10  9  8  7  6  5  4  3  2  1
  bottom row: 26 25 24 23 22 21 20 19 18 17 16 15 14
  -> pin 1 = top RIGHT; top row numbers 1->13 right-to-left;
     bottom row 14 sits under pin 1, numbers 14->26 right-to-left.

GREEN connector = C274 (12-way), connector face:
  top row:     5  4     3  2  1
  bottom row: 12 11    10  9  8  7  6
  -> pin 1 = top RIGHT; centre key between the groups.
```

⚠️ Confirm this is the **face** (mating) side vs the wire-entry side on your actual
plug before probing — mirror left/right if you're looking at the back.

Central-locking wires shown in the graphic (all match the tables below):
| Pin | Wire | Drives |
|---|---|---|
| C225 pin 7 | YK (yellow) | Driver's door lock actuator — **position SENSE**, not drive (see direction-sensing §) |
| C274 pin 2 | O (orange) | Passenger's door lock actuator |
| C274 pin 3 | K (pink) | door lock actuators (other direction) |
| C274 pin 11 | B (black) | ground |

## Connector C225 (the GREY ~26-way on the bench unit)

| Pin | Wire | Function | Category |
|---|---|---|---|
| 1 | WP | LH-front-door + tailgate ajar sense (X150, X265 via Z277 diode) | Perimetric input |
| 3 | WB | Volumetric alarm sensor (X213) | Input |
| 5 | PG | Door ajar sense via left seat-power relay diode (Z223) | Perimetric input |
| 7 | YK | **Driver's-door lock-actuator (M114) POSITION switch** — Lock/Unlock state feedback ⭐ | **Input (latch state)** |
| 8 | UG | LH front door key switch (X201) — momentary "key operated", **no direction** | Input |
| 9 | PO | Bonnet switch (X212) | Perimetric input |
| 10 | GK | **+12 V feed** — Satellite Fuse Box 1, F5 (10 A) | **Power** |
| 11 | RS | → ECM C1032 pin 22 (shared with MIL line) | ECM link (verify) |
| 13 | SCR | Antenna screen/shield | RF |
| 15 | B | **→ ECM C1017 pin 26 = coded MOBILISE line** | **ECM link ⭐** |
| 16 | PW | Door switch sense (via MFU Z148) | Perimetric input |
| 17 | KB | **→ diagnostic serial line** (car: OBD-II DLC pin 8) | **Comms ⭐** |
| 18 | PR | Window Lift ECU (Z147) link | Link |
| 20 | BN | Volumetric alarm sensor (X213) | Input |
| 25 | P | **+12 V feed** — Satellite Fuse Box 1, F1 (15 A) | **Power** |
| 26 | WB | Antenna (receiver) | RF |

## Connector C274 (the GREEN ~12-way on the bench unit)

| Pin | Wire | Function | Category |
|---|---|---|---|
| 1 | GW | Direction indicators RH (hazard flash) | Output |
| 2 | O | Central-locking actuator drive | Output |
| 3 | K | Central-locking actuator drive | Output |
| 4 | RW | Theft-alarm LED (instrument cluster Z142) | Output |
| 5 | PO | Horn relay trigger (K189) | Output |
| 6 | GR | Direction indicators LH (hazard flash) | Output |
| 8 | PN | **+12 V feed** — Engine bay fuse box, F4 (30 A) | **Power (lock motors, 30 A)** |
| 10 | BO | Park/neutral → engine crank inhibit | Input |
| 11 | BO | **Ground** (S204 → E200) | **GND** |

## How the 10AS senses key-turn DIRECTION (EKA entry) ⭐

Source: RAVE `etlj970x.pdf` §T2 circuit page 7 (driver's-door circuit) +
page 8 (lock-motor bus) + page 4 ("Perimetric Testing"). This is the piece the
documented EKA procedure needs to be bench-drivable.

The documented EKA procedure enters a 4-digit code at the driver's door by
turning the key an alternating **UNLOCK / LOCK / UNLOCK / LOCK** count. For that
the 10AS must distinguish a lock turn from an unlock turn — but the **key switch
does not carry direction**:

- **C225 pin 8 (UG) — X201 Left Front Door Key Switch.** RAVE draws it as a
  SINGLE momentary switch (`[1] Key turned` / `[2] Key out`), one wire to pin 8,
  other side to ground (via C504 p4 → S501 → E201). It grounds pin 8 **whenever
  the key is turned in the barrel, either way.** No lock/unlock distinction.

Direction comes from a **second input** — the driver's-door lock **position**:

- **C225 pin 7 (YK) — M114 Left Front Door Lock Actuator POSITION switch.**
  Page 7 draws M114 here as a switch with `[1] Lock` / `[2] Unlock`, wired
  pin 7 → C2101 p6 → C507 p5, other side to ground (C507 p3, B). It reports the
  **mechanical lock state** of the driver's door back to the 10AS.
  ⚠️ This corrects our earlier table + the community graphic, which called pin 7
  a "lock drive output." It is an **INPUT (lock-state sense)**, not a drive.

The lock **motors** are driven separately — page 8 shows all five actuators
(M114/M122/M117/M125/M132 motor windings) fed by the **C274 pin 2 (O)** and
**pin 3 (K)** bus. So on C225, pin 7 is sense-only.

**Direction logic (inferred):** each key operation = a pin-8 pulse; the 10AS
then reads pin 7 to see which position the lock ended in (Lock vs Unlock) and
counts operations per direction. Combined with the alternating UNLOCK→LOCK→…
digit pattern, that yields the 4 digits.

### Bench simulation of EKA — the minimum signal set

To drive an EKA attempt on the bench you would need to reproduce BOTH signals,
not just pin 8:

| Signal | 10AS pin | Bench action |
|---|---|---|
| "Key operated" pulse | C225 **pin 8 (UG)** | momentary switch/GPIO to ground, one pulse per turn |
| Lock-state feedback | C225 **pin 7 (YK)** | hold to ground for one state, open for the other, matching the digit's direction |
| Precondition: all closed | pins 1 (WP), 16 (PW), 5 (PG), 9 (PO) | leave OPEN (= all doors/bonnet shut) so the module accepts entry |

⚠️ **Unknowns before this can work:** (1) the exact SENSE of pin 7 — which state
(grounded vs open) the M114 switch presents for Lock vs Unlock; (2) the precise
timing the 10AS expects between the pin-8 pulse and the pin-7 settle; (3) whether
NAS units even enable door-lock EKA (the diag.net thread notes the **NAS owner's
manual omits EKA** and points to the remote — a real risk this path is disabled
on our 315 MHz NAS unit). All three are bench-probe questions. Lockout after ~3
bad attempts means **don't brute-force by turning the key** — model it in software
against the K-line first if the 10AS diagnostic protocol is ever mapped.

## Minimal bench rig

Four wires power it and let you talk to it; add two more to mobilise a GEMS ECM.

| Purpose | 10AS pin | Wire | Connect to |
|---|---|---|---|
| Logic power (feed both) | C225 pin 25 | P | +12 V |
| Logic power (feed both) | C225 pin 10 | GK | +12 V |
| Ground | C274 pin 11 | BO | Bench GND (**shared with ECM GND**) |
| Diagnostics (read EKA) | C225 pin 17 | KB | Adapter K-line (via L9637D) |
| Coded mobilise → ECM | C225 pin 15 | B | GEMS ECM **C1017 pin 26** |
| *(optional)* lock-motor power | C274 pin 8 | PN | +12 V (only to drive central locking) |

Notes:
- The 10AS has **two logic feeds** (pins 25 + 10); one is a permanent battery feed
  (alarm armed with ignition off), the other ignition-switched. The fuse-detail
  page would say which; on the bench just feed **both**.
- **C274 pin 8 (30 A)** is only the high-current supply for the door-lock actuator
  motors — not needed to power the logic or read the EKA.

## Direct 10AS ↔ GEMS ECM wires (NOT over the K-line)

| 10AS pin | Wire | ECM pin | Purpose | Confidence |
|---|---|---|---|---|
| C225 pin 15 | B | C1017 pin 26 | Coded **mobilise** ("no code, no start") | **Confirmed** (RAVE + SM001) |
| C225 pin 11 | RS | C1032 pin 22 | Shared with MIL line — likely status sense | Needs verification |

For a "10AS mobilises the GEMS ECU on the bench" rig, the load-bearing wire is
**C225 pin 15 → ECM C1017 pin 26**, plus a **common ground** between the two
units. Even correctly wired, the 10AS may only emit the mobilise code once it
considers itself **disarmed** (valid handset/key event or EKA entry) — which is
why reading/using the EKA matters. Ties to the [EKA read from the Lucas 10AS] and
[unlock the immobiliser from the bench] backlog items.

### Does pin 15 need to go through the Pico? No (for pairing).

The mobilise line is a **direct hardware handshake** between the 10AS and the ECM:
the 10AS emits its coded signal, the ECM compares it to its stored code and
un-inhibits fuel/injectors if they match. To **pair / mobilise on the bench you do
NOT need to read pin 15** — just wire it 10AS→ECM and let them talk. You'd only
need to tap pin 15 (logic analyzer or a spare GPIO — *not* the L9637D K-line path)
if the goal becomes **capturing or spoofing** the mobilise code (an unknown coded
protocol, separate RE effort). Decide that later; pairing comes first.

## Pairing the ECM to the 10AS (bench)

**First, the deciding question — same vehicle or not?**

| Situation | What's needed |
|---|---|
| 10AS + ECM from the **same** car | Codes already match → **just wire + disarm**, no software step |
| 10AS + ECM from **different** cars | Codes mismatch → run **Security-Learn** (`A300622588`, unvalidated) to teach the ECM the 10AS code |

**Wire it (minimal pairing rig):**

| From (10AS) | To | Purpose |
|---|---|---|
| C225 pin 25 + pin 10 | +12 V | 10AS logic power (feed both) |
| C274 pin 11 | Bench GND (**shared with ECM GND**) | ground |
| C225 pin 15 | ECM C1017 pin 26 | coded mobilise |
| — | ECM normal bench power/ground | ECM alive |
| — | ECM C1033 pin 8 = +12 V | ignition sense on |

**The disarm problem** — the 10AS only emits "mobilise" when it thinks it's
disarmed. On the bench (no synced handset, no doors), disarm paths, easiest first:
1. **Power-up state** — RAVE: the 10AS "remembers the state it was left in." If
   pulled from the car disarmed, it may **power up disarmed**. Try this first (may
   need nothing).
2. **Key-switch input** — pulse **C225 pin 8 (UG)** per the X201 key-switch logic
   (exact sense TBD).
3. **EKA over the K-line** (pin 17) — the proper way, but the 10AS protocol is not
   mapped yet (the research payoff).
4. **Handset** — only if one is synced to this unit.

**How you'll know it worked** — re-run the bench actuator probe: routines that were
gated by immobilisation (fuel-pump `$31`, injectors — pin 24 C1032 etc.) should now
**fire** instead of returning `conditionsNotCorrect`. That's the pass/fail signal.

⚠️ **Bench danger** — do **not** fire `A300622588` (Security-Learn) casually; it
pairs the ECM to whatever body module is present and can leave the ECM immobilised
if wrong. Only use it when the two are *known mismatched*, and treat it as an
experiment.
