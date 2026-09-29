# Two-board rig — universal adapter (Board 1) + bench hub (Board 2)

Design set by the user 2026-09-27. This is the current, preferred physical
architecture and it **revises** the older two-box package
(`hardware/gems-2pcb/`, `diagrams/gems-2pcb-solution.html`): the Board 1 ↔ Board 2
link is now an **OBD2 connector** (not the old 4-pin Molex J1/J3), **Board 1 is
fully car-capable on its own** (so the Vs protection lives on it), and **Board 2
adds a 10AS branch** alongside the ECU branch. Perfboard first; the same nets fold
back into the JLCPCB package later.

## Concept

- **Board 1 — MAIN / universal adapter.** Pico + L9637D + microUSB (Pico logic
  power) + **one male J1962 (OBD2) plug**. That plug is the only external
  interface. It goes into **a real car** OR into **Board 2**. 12 V + K + L + GND
  all arrive on that OBD2 plug. The K-line pull-up, the Vs TVS and the fuse all
  live here so Board 1 is safe in either mode.
- **Board 2 — BENCH hub / go-between.** A **female J1962 socket** receives Board
  1, a **DC barrel jack** brings in bench 12 V, and **screw terminals / headers**
  fan 12 V / GND / K / L out to the **ECU** and to the **10AS**. Board 2 makes the
  hand-wired ECU + 10AS look like "a car" to Board 1. Used only on the bench.

```
CAR MODE:     [Board 1 male OBD2] ─► car J1962 (female)
BENCH MODE:   [Board 1 male OBD2] ─► [Board 2 female OBD2] ─► screw terminals ─► ECU + 10AS
                                          ▲
                                    DC 12 V adapter
```

Connector genders (locked, Option A): **Board 1 = male J1962**, **Board 2 =
female J1962**. Board 2's outputs to the ECU/10AS are **screw terminals**, not
another OBD plug.

### Build method — everything lands on PCB-mount screw terminal blocks

Decided 2026-09-27. **No OBD2 connector is soldered directly to a board.** The
J1962 connectors are **pigtails** (a moulded OBD2 plug/socket on a short flying
harness); each wire in the pigtail screws into a **PCB-mount screw terminal
block** on the perfboard. So on every board the *board-side* of each interface is
a screw terminal block:

- **Board 1:** a **male J1962 pigtail** → its wires screw **directly** into the
  9-terminal block described below (A1/A2/A3, B1/B2/B3, GND, GND, 12V). There is
  no separate "patch bank" downstream of a J1962 terminal block — the terminals
  ARE the pigtail termination points. **Reconfiguring which vehicle line goes to
  which transceiver channel = physically moving which pigtail wire is screwed into
  which terminal** — that's the whole point of screw terminals over solder joints.
- **Board 2:** a **female J1962 pigtail** → screw terminal block; plus the DC
  jack, the ECU terminal block and the 10AS terminal block.

This keeps the OBD2 mechanics off the copper (cleaner, serviceable, no fragile
connector-to-board solder joints) and means the whole rig is screw-terminal wiring
end to end. Pick blocks rated for the current (the +12 V / ECU-power contacts carry
a few amps — 5 mm-pitch blocks are ample; K/L/GND signal contacts can be smaller).

## Multi-vehicle scope & architecture

Set 2026-09-27. The hardware is **not GEMS-specific** — it is a **universal
pre-CAN K-line adapter**. GEMS is simply the first vehicle it speaks to.

### What it can and cannot reach (a hardware envelope, not a firmware limit)
The **L9637D is a purpose-built K-line / ISO 9141 transceiver** (ST Doc ID 1765,
"Monolithic bus driver with ISO 9141 interface"): one bidirectional **K** pin +
an **L** comparator (sense only — it does *not* drive L). That silicon choice sets
the envelope:

| Bus | OBD pins | This device? |
|---|---|---|
| **ISO 9141-2 / ISO 14230 (KWP2000)** K-line | 7 (K), 15 (L) | ✅ **yes** — its whole purpose |
| **CAN** (ISO 11898) | 6, 14 | ❌ no — needs a CAN transceiver + controller; different silicon |
| **J1850** PWM/VPW (Ford/GM) | 2, 10 | ❌ no — different physical layer |

So the reach is the **K-line family, roughly 1996–2005 pre-CAN** (heavy on
European/Asian makes). CAN is a hardware wall, not a firmware gap.

### One adapter · one firmware · many host profiles
The Pico firmware is a **dumb, generic timed K-line byte pipe** (5-baud/fast init,
byte timing, half-duplex echo cancellation, framing-by-timeout). **All
vehicle-specific intelligence lives in the Python host**, so switching cars is a
**profile swap in software — no reflashing.**

| Layer | Varies per car? | Reflash to switch? |
|---|---|---|
| Board 1 + Board 2 hardware | no — identical | — |
| Pico firmware | no — one generic pipe | **No** |
| Host profile (Python) — init address, keybytes, baud, L-mode, service/PID map, upper protocol | **yes** | **No — just select the profile** |

**GEMS is one host profile** (`protocol/obd.py`, `gems_secure.py`); other 1990s
K-line cars are additional profiles. The GEMS-flavoured firmware bit (the keybyte
handshake) is really just the standard ISO 9141-2 handshake; `CMD_INIT` already
takes a baud parameter and `CMD_RAW_INIT` / `CMD_RAW_XFER` give raw access, so the
firmware is already ~90 % generic.

**Firmware changes only for a new *generic* low-level primitive**, never per-car —
e.g. driving the L-line for 5-baud-init cars that need it (see below), or an
unusual init variant. You add it as a capability the host invokes, not as a
GEMS-vs-other build split.

### The one hardware addition that makes it truly universal: an L-line driver
The L9637D can *sense* L but **cannot drive it**. Some pre-CAN ECUs (older VAG
KWP1281, some Mercedes/BMW/Opel) require the 5-baud init address **driven on the
L-line**, then released — a GEMS passive strap won't serve them. To be universal,
Board 1 should add a **small external open-collector L driver** (one Pico GPIO →
~1 kΩ → NPN/MOSFET pulling the L net low, with a pull-up), which is exactly the
classic KKL-cable topology (L9637D for K + a transistor for L). The three L modes
are then **mutually exclusive per session**: K-only, K + driven-L, or K + L↔K
strap (GEMS/JP1) — don't drive L while it's strapped to K. See the L-line notes
below; the GEMS-simple build omits the driver, the universal build adds it.

## J1962 (OBD2) pins used

| OBD pin | Signal |
|---:|---|
| 4 | Chassis ground |
| 5 | Signal ground |
| 7 | **K-line** |
| 15 | **L-line** |
| 16 | **+12 V** |

(4 and 5 are both tied to the common ground here.)

---

## Board 1 — MAIN (universal adapter)

### Parts
| Ref | Part | Notes |
|---|---|---|
| U2 | Raspberry Pi Pico / Pico 2 (W) | powered over **microUSB** |
| U1 | ST L9637D (SO-8) | K-line transceiver; on a SO-8→DIP breakout for perfboard |
| R1 | **510 Ω** | K→Vs pull-up — **required** |
| D1 | **1.5KE24A** TVS (24 V, uni) | Vs clamp — **populated** (Board 1 is car-capable) |
| F1 | **1–2 A** fuse (inline/holder) | on the +12 V (OBD pin 16) feed |
| C1 | 100 nF ceramic | Vcc decoupling (optional) |
| JP1 | 2-pin header + shunt | **L↔K tie** (fit for bench/proprietary; pull for plain car OBD) |
| P1 | **male J1962 pigtail** + 5-way PCB screw terminal block | the one external interface; pigtail leads screw in (12V/GND/GND/K/L) — no OBD housing on the board |

### Nets
```
OBD.16 (+12V) ── F1 ── D1(TVS)→GND ── U1.7 (Vs)
U1.7 (Vs) ── R1 510Ω ── U1.6 (K)               [K node]
U1.6 (K)  ── OBD.7  (K-line out)
OBD.15 (L) ── JP1 ── U1.6 (K node)             [L↔K tie, removable]
U1.3 (Vcc) ── Pico 3V3 ;  C1 0.1µF U1.3→GND
U1.4 (TX) ── Pico GP0  ;  U1.1 (RX) ── Pico GP1
U1.8 (LI) ── GND       ;  U1.2 (LO) ── n/c
GND net: U1.5 + Pico GND + OBD.4 + OBD.5        [star ground]
Pico USB ── laptop/charger (5 V + data)         [12 V NEVER touches the Pico]
```

Notes:
- **Vcc = 3.3 V from the Pico, never 5 V** (RX idles at Vcc → would injure GP1).
- **12 V lands only on U1 pin 7.** Verify L9637D pin-1 orientation before power.
- TVS + fuse are populated here so Board 1 is protected **in the car**; on the
  clean bench 12 V they simply sit idle.

### L-line handling (GEMS-simple vs universal)

The L9637D's L pins are a **comparator — sense only; it does NOT drive L** (Doc ID
1765, pin 2 LO / pin 8 LI). K and L are kept as **separate nets**; how L is used
is a build choice:

- **GEMS-simple build (default):** L (OBD.15) → **JP1** → K node. L9637D LI→GND,
  LO→n/c. Passive strap only — this is what opens the GEMS **0xDA** channel. No
  L driving.
- **Universal build (multi-make):** add an **external open-collector L driver** so
  firmware can drive the 5-baud init on L for cars that need it:
  ```
  Pico GPIO(Ldrv) ── ~1kΩ ── base/gate of NPN/N-MOSFET ── open-collector → L net
  L net ── pull-up (to L-bus rail via ~510Ω–1k)
  (optional L sense: L net → U1.8 LI ;  U1.2 LO → Pico GPIO)
  ```
  Keep **JP1** too (for the GEMS strap). The three L modes are **mutually
  exclusive per session** — K-only, K+driven-L, or K+strap — never drive L while
  JP1 straps it to K (the L driver would fight the K driver). A firmware/profile
  interlock enforces this.
- **Protection:** with JP1 closed, L joins the K node and shares its 510 Ω pull-up
  + Vs TVS. When JP1 is open and L is undriven, the L pin floats — harmless. The
  external driver transistor should be rated for the 12 V L-bus (≥40 V part).

### Finalized Board 1 I/O — the 9-terminal block IS the OBD pigtail termination (2026-09-27, terminal scheme CORRECTED 2026-09-29)

Board 1 has **ONE terminal block, stacked two rows, 9 terminals total** — and the
OBD pigtail wires land **directly** on these terminals. There is no separate
downstream "patch bank" — the terminals themselves are both the pigtail
termination point AND the transceiver-channel selector. **The screw terminals ARE
the reconfiguration mechanism**: to change which vehicle line a channel talks to,
you physically move which pigtail wire is screwed into which terminal.

```
ONE ROW:    [ A1 ][ A2 ][ A3 ]   [ B1 ][ B2 ][ B3 ]   [ 12V ]   [GND ][GND ]
```

Each terminal has a fixed internal trace to a transceiver pin; each pigtail wire
is landed wherever you want that OBD line to go:

| Terminal | Internal net | Current build's pigtail wire |
|---|---|---|
| **A1** | U1 pin 6 (K) | OBD **pin 7** (engine K-line) |
| **A2** | U1 pin 6 (K) — **same node as A1**, 2nd slot | OBD **pin 15** (L-line) — **intentionally tied to A1**, so U1 always has the GEMS 0xDA L↔K strap open |
| **A3** | U1 pin 8 (LI) — read-only listen tap | not currently used |
| **B1** | U3 pin 6 (K, secondary channel) | OBD **pin 8** (10AS diagnostic bus) |
| **B2** | U3 pin 6 (K) — same node as B1, 2nd slot | not currently used |
| **B3** | U3 pin 8 (LI) — read-only listen tap | not currently used |
| **GND** | common ground | OBD pin 4 |
| **GND** | common ground | OBD pin 5 |
| **12V** | fuse → TVS → {Vs, buck} | OBD pin 16 |

- **A1/A2 are ONE electrical node** (same for B1/B2) — whatever's landed on either
  is tied together permanently until a wire is physically moved. **A3/B3 are
  separate, read-only LI nodes**, isolated from the K nodes.
- **A1+A2 tied to pins 7+15 is a deliberate design choice for this build** — it
  keeps U1's 0xDA channel permanently open rather than optional/removable. To go
  back to plain OBD (no L↔K strap), unscrew the pin-15 wire from A2. To route L
  elsewhere instead (e.g. if not using the immobiliser work), move it to B1/B2/B3
  as needed — **that's the reconfiguration model: move wires between screws, not
  jumpers or code.**
- LO (U1 pin 2 / U3 pin 2) is **not** a terminal — it's a fixed internal wire
  straight to the Pico (**GP2** / **GP6**), since it's the comparator's output *to*
  the microcontroller, never something an external pigtail wire connects to.
- **The other 10 OBD pins** (1, 2, 3, 6, 9, 10, 11, 12, 13, 14 — incl. CAN 6/14 and
  J1850 2/10) are simply **not landed on any terminal** in this 9-terminal build.
  Out of scope for the L9637D; add more terminal slots later if a use-case needs
  them (no respin — same perfboard/PCB, more terminals).
- This subsumes JP1 — a dedicated jumper header is not needed; the terminal screws
  do that job.

Verified DLC pin meanings per model live in **`docs/dlc-pinouts.md`** (Disco 1:
10AS on pin 8; P38: BeCM shares 7/15). Reaching the **10AS needs OBD pin 8**, not 7.

### Immobiliser-line sniffer — the spare L channel as a 12 V-safe monitor

The L9637D's L channel is **read-only (LI→LO, sense; can't drive)** — which makes it
the *right* tool to passively watch the coded **mobilise line** (10AS C225 p15 →
ECM C1017 p26) **while K drives the engine**: two channels, one chip, no 2nd
transceiver, and LI is **12 V-rated** (a bare Pico GPIO would be destroyed).

```
10AS C225 p15 ──┬──► ECU C1017 p26     (mobilise — unchanged, still works)
                └──► terminal A3 (or B3) ──► L9637D LI (pin 8)  (high-Z read-only, no pull-up/cap)
L9637D LO (pin 2) ──► Pico GP2 (physical pin 4)   (3.3 V digital copy; internal pull-up)
+ common ground between L9637D, 10AS, ECM; board powered.
```

- **No pull-up, no cap** on LI (the mobilise line is *actively driven* by the 10AS,
  so nothing needs to hold it; a pull-up could fight an unknown driver type) or on
  LO→GP2 (a cap would smear the edges).
- **Firmware:** `CMD_MONITOR_L` (0x09), added in `pico_kline_all` **3.5.0** —
  captures digital transitions on GP2 over a window and returns the edge timing.
- ⚠️ **Must be verified on the bench** — this captures a *digital* line; we don't
  yet know the mobilise signal's waveform. Characterize once (scope best; or the
  monitor itself). Zero transitions = static line **or** a signal the 1-bit
  comparator can't resolve — a scope disambiguates. Not proof of "no signal."

### DUAL transceiver — U1 + U3, two K-line channels (DECIDED 2026-09-28)

Board 1 now carries **TWO L9637D transceivers** so it can drive **two independent
K-line channels at once** — engine on one, a second module (10AS / EAS / SRS) on the
other — with **independent baud** (engine 10400, 10AS 9600) on the RP2040's two
hardware UARTs. This is what the immobiliser relearn wants (ECM learn session live
on U1 *while* commanding the 10AS on U3) and what multi-line vehicles need (P38
engine on pin 7 *and* EAS on 11/12 concurrently).

| | **U1 — K-line #1 (engine)** | **U3 — K-line #2 (10AS/EAS/SRS)** |
|---|---|---|
| UART | **UART0 / `Serial1`** | **UART1 / `Serial2`** |
| TX (4) | Pico **GP0** | Pico **GP4** (`Serial2.setTX(4)`) |
| RX (1) | Pico **GP1** | Pico **GP5** (`Serial2.setRX(5)`) |
| LO (2) | Pico **GP2** (fixed wire, not a terminal) | Pico **GP6** (fixed wire, not a terminal) |
| K (6) | **R1 510 Ω → Vs**; terminals **A1/A2** (dflt pin 7) | **R2 510 Ω → Vs**; terminals **B1/B2** (dflt pin 8) |
| LI (8) | terminal **A3** (read-only listen tap) | terminal **B3** (read-only listen tap) |
| Vs (7) / Vcc (3) / GND (5) | shared 12 V (fused+TVS) / 3V3 / GND | same shared rails |

- **Two K nodes, kept SEPARATE** — each has its own 510 Ω pull-up and its own
  A1/A2 (or B1/B2) terminal pair. **Never short the two K nodes** (that recreates
  the shared-node contention that broke the 10AS probing).
- **Shared power** — both chips off the one fused (1 A) + TVS 12 V node and the
  Pico 3V3. One fuse still covers both. (GP8/GP9 are the no-config UART1 default if
  you'd rather not `setTX/setRX`.)
- **Firmware TODO (hardware ready, U3 idle until then):** add a **`channel` byte**
  (0 = U1/Serial1, 1 = U3/Serial2 at its own baud) to the K-line commands
  (`CMD_INIT` / `CMD_SEND_RECV` / `CMD_RAW_XFER` / `CMD_MONITOR_L` / `CMD_CAPTURE`),
  mirroring the existing Serial1 handlers onto Serial2.

### On-car power — OBD 12 V powers the Pico (route A, DECIDED 2026-09-28)

Board 1 is **self-powered on a running truck** — no separate 5 V brick. USB is now
**optional** (data/flashing only).

```
OBD pin 16 (+12 V) ─[F1 1A]─┬─[TVS 1.5KE24A]─► U1 Vs + U3 Vs
                            └─► BUCK 12→5V (fixed, 5–30 Vin, 3 A) ─► 1N5817 ─► Pico VSYS (pin 39)
```
- **1N5817** (band toward Pico) diode-ORs the buck with USB **automatically — no
  switch**. Two sources at ~5 V share/priority safely; VSYS never exceeds ~5 V and
  never sees 12 V (the buck steps it down first). **Feed VSYS (39), NEVER VBUS (40).**
- Fixed-5V buck is fine (VSYS ~4.7 V after the Schottky). Optional belt-and-braces
  vs a *failed* buck: a ~5.6–6.2 V Zener/TVS on VSYS→GND.
- Buck taps the 12 V **after** F1 (one fuse covers L9637D×2 + buck).

This resolves the long-parked "route A" power decision; it supersedes the earlier
"USB-only" note above.

---

## Board 2 — BENCH hub

### Parts
| Ref | Part | Notes |
|---|---|---|
| P2 | **female J1962 pigtail** + PCB screw terminal block | receives Board 1; pigtail leads screw in — no OBD housing on the board |
| J2 | DC barrel jack (2.1 mm) | bench 12 V in |
| D2 | Schottky (SS54 / 1N5822) | reverse-polarity protect on the DC input |
| F2 | **2 A** fuse + holder | main bench fuse |
| SW1 | SPST toggle (≥5 A) | master 12 V (PWR) |
| SW2 | SPST toggle (≥3 A) | ECU **ignition** feed (C1033 p8) |
| TB-ECU | screw terminal block | out to the ECU |
| TB-10AS | screw terminal block | out to the 10AS |

### Nets
```
J2 (+12 in) ── D2 (rev-pol) ── F2 (2A) ── SW1 ── V12S rail

V12S ── P2.16                         (+12 up to Board 1 / L9637D Vs)
V12S ── TB-ECU:+12main                (ECU C1033 pin 7)
V12S ── SW2 ── TB-ECU:+12ign          (ECU C1033 pin 8)
V12S ── TB-10AS:+12  (×2)             (10AS C225 pin 25 AND pin 10 — feed both)

P2.7  (K) ── TB-ECU:K  ── TB-10AS:K   (ECU C1017 p23  +  10AS C225 p17)   [shared K bus]
P2.15 (L) ── TB-ECU:L                 (ECU C1017 p20 only — 10AS has no L)

GND (J2−) ── P2.4 ── P2.5 ──
             TB-ECU:GND (ECU C1033 p5/p9/p10/p16) ──
             TB-10AS:GND (10AS C274 p11)                                  [star ground]
```

### The one wire that is NOT on either board
The **coded mobilise line** is a direct 10AS→ECM wire, not a bus signal:

```
10AS C225 pin 15  ──────────►  ECU C1017 pin 26      (coded MOBILISE; "no code, no start")
```

Run it point-to-point between the two units (or as a pass-through pair on Board 2);
keep a **common ground** between 10AS and ECU (already shared above). This is what
lets the 10AS mobilise the ECM on the bench — see `docs/10as-pinout.md`.

---

## Signal flow, both modes

| Signal | Car mode | Bench mode |
|---|---|---|
| +12 V | car OBD pin 16 → Board 1 | DC adapter → Board 2 → OBD pin 16 → Board 1 |
| K-line | Board 1 ↔ car ECU (OBD pin 7) | Board 1 ↔ Board 2 → ECU C1017 p23 **and** 10AS C225 p17 |
| L-line | Board 1 JP1↔K, OBD pin 15 → car | Board 1 JP1↔K, OBD pin 15 → Board 2 → ECU C1017 p20 |
| GND | car OBD pin 4/5 | DC adapter → Board 2 → OBD pin 4/5 + ECU + 10AS |
| Pico logic | microUSB 5 V (always) | microUSB 5 V (always) |

**Power is inherently single-source:** Board 1 is *either* in the car *or* in
Board 2, so OBD pin 16 only ever has one 12 V origin. Never power the bench from
the DC adapter while Board 1 is also in a car.

## Build / safety checklist
1. **Connector genders:** Board 1 male, Board 2 female. Board 2→ECU/10AS = screw
   terminals, not OBD.
2. **L9637D pin-1 orientation** confirmed before any power; **Vcc = 3.3 V**.
3. **JP1 fitted** for bench/proprietary (0xDA) work; pull it for plain car OBD.
4. **Star ground** ties DC-adapter GND, both OBD grounds, ECU GND, 10AS GND, Pico
   USB GND to one point — avoids loops between the three boxes.
5. First contact **read-only** (`gems_t4 kline live`), writes proven on the
   virtual ECU first.
6. On a **running vehicle**: F1 + D1 (TVS) on Board 1 are what make that safe —
   they're populated by design here.

## Relationship to the JLCPCB package
`hardware/gems-2pcb/` still documents the fab/BOM mechanics (fab settings, LCSC
C-numbers, trace widths, assembly split). This doc supersedes its **topology**:
the 4-pin Molex Board1↔Board2 link (J1/J3) becomes the **OBD2 pair**, the Vs
TVS/fuse move to **Board 1 (populated, not DNP)**, and Board 2 gains the **10AS
terminal block** in addition to the ECU one. Fold these nets back into the package
when the perfboard build is proven and you move to fabbed boards.
