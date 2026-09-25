# Lucas 10AS / Theft Alarm Unit (Z163) — pinout & bench wiring

**Source:** RAVE electrical troubleshooting manual `etlj970x.pdf` (1997 NAS
Discovery 1), section **T2 "THEFT ALARM SYSTEM (NAS)"**, pages 322–336. This is
the authoritative circuit for the user's exact truck. RAVE labels the Lucas 10AS
the **"Theft Alarm Unit (Z163)"**; it has two connectors, **C225** (multiway) and
**C274**.

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

## Connector C225

| Pin | Wire | Function | Category |
|---|---|---|---|
| 1 | WP | Door/tailgate switch sense | Perimetric input |
| 3 | WB | Volumetric alarm sensor (X213) | Input |
| 5 | PG | Door switch sense / seat-relay diode | Perimetric input |
| 7 | YK | Central-locking **lock** drive | Output |
| 8 | UG | LH front door key switch (X201) | Input |
| 9 | PO | Bonnet switch (X212) | Input |
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

## Connector C274

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
