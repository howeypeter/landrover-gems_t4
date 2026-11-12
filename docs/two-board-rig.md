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
- **Board 2:** a **female J1962 pigtail** → **soldered** to a fixed 16-pad block
  (⚠️ corrected 2026-10-05 — see the Board 2 section below: this one is soldered,
  not screwed, with a separate patch-screw layer downstream); plus the DC jack,
  the ECU terminal block and the 10AS terminal block.

This keeps Board 1's OBD2 mechanics off the copper (cleaner, serviceable, no
fragile connector-to-board solder joints there) while Board 2 takes the opposite
tradeoff deliberately (solder the pigtail, screw the patch layer) — see the Board 2
section for why. Pick blocks rated for the current (the +12 V / ECU-power contacts
carry a few amps — 5 mm-pitch blocks are ample; K/L/GND signal contacts can be
smaller).

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
strap (GEMS, via terminal A2) — don't drive L while it's strapped to K. See the L-line notes
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

**Full electrical detail (BOM, every pin, every net) lives in the standalone
reference: [`diagrams/PCB_Board_Scheme/PCB_Board_Scheme.md`](../diagrams/PCB_Board_Scheme/PCB_Board_Scheme.md).**
That file is the single source of truth for exact refdes/pins/nets; this doc
stays narrative/rationale-focused to avoid the two drifting apart.

**Reference designators (locked 2026-09-29): U1 = Pico 2 W** (host MCU),
**U2 = L9637D** (primary/engine channel), **U3 = L9637D** (secondary channel).

- **Vcc = 3.3 V from the Pico, never 5 V** (RX idles at Vcc → would injure the
  Pico's GPIO).
- **12 V lands only on U2/U3 pin 7 (Vs) and the buck input.** Verify L9637D
  pin-1 orientation before power.
- **TVS (D1) + fuse (F1)** are populated so Board 1 is protected **in the
  car**; on the clean bench 12 V they simply sit idle.

### L-line handling (GEMS-simple vs universal)

The L9637D's L pins are a **comparator — sense only; it does NOT drive L** (Doc ID
1765, pin 2 LO / pin 8 LI). K and L are kept as **separate nets**; how L is used
is a build choice — implemented via the terminal scheme below (see "Finalized
Board 1 I/O"), **not a dedicated jumper**:

- **GEMS-simple build (this build):** L (OBD pin 15) lands on terminal **A2**,
  which is tied to A1 (K). Passive strap only — this is what opens the GEMS
  **0xDA** channel. No L driving. LI (U2 pin 8) is free for a listen-only tap
  (terminal A3); LO (U2 pin 2) goes straight to Pico GP2.
- **Universal build (multi-make):** add an **external open-collector L driver** so
  firmware can drive the 5-baud init on L for cars that need it:
  ```
  Pico GPIO(Ldrv) ── ~1kΩ ── base/gate of NPN/N-MOSFET ── open-collector → L net
  L net ── pull-up (to L-bus rail via ~510Ω–1k)
  ```
  The three L modes are **mutually exclusive per session** — K-only, K+driven-L,
  or K+strap (A2 landed) — never drive L while it's also strapped to K via A2
  (the L driver would fight the K driver). A firmware/profile interlock enforces
  this; moving the A2 wire is the physical interlock for now.
- **Protection:** with A2 landed (strapped), L joins the K node and shares its
  510 Ω pull-up + Vs TVS. With A2 unused and L undriven, the L pin floats —
  harmless. The external driver transistor should be rated for the 12 V L-bus
  (≥40 V part).

### Finalized Board 1 I/O — the 9-terminal block IS the OBD pigtail termination (2026-09-27, terminal scheme CORRECTED 2026-09-29)

Board 1 has **ONE terminal block, one row, 9 terminals total** — and the
OBD pigtail wires land **directly** on these terminals. There is no separate
downstream "patch bank" — the terminals themselves are both the pigtail
termination point AND the transceiver-channel selector. **The screw terminals ARE
the reconfiguration mechanism**: to change which vehicle line a channel talks to,
you physically move which pigtail wire is screwed into which terminal.

```
ONE ROW:    [ A1 ][ A2 ][ A3 ]   [ B1 ][ B2 ][ B3 ]   [ 12V ]   [GND ][GND ]
```

**Board silkscreen names:** `K1-A`=A1, `K1-B`=A2, `K1-RO`=A3, `K2-A`=B1,
`K2-B`=B2, `K2-RO`=B3 — same six physical terminals; the board prints the K1/K2
names, this doc keeps the A/B lettering.

Each terminal has a fixed internal trace to a transceiver pin; each pigtail wire
is landed wherever you want that OBD line to go. **Full 6-terminal assignment
FINALIZED (2026-10-20):**

| Terminal | Internal net | Current build's wire |
|---|---|---|
| **A1** (`K1-A`) | U2 pin 6 (K) | OBD **pin 7** (engine K-line) |
| **A2** (`K1-B`) | U2 pin 6 (K) — **same node as A1**, 2nd slot | OBD **pin 15** (L-line) — **intentionally tied to A1**, so U2 always has the GEMS 0xDA L↔K strap open |
| **A3** (`K1-RO`) | U2 pin 8 (LI) — read-only listen tap | OBD **pin 13** (SRS/airbag diagnostic line). Passive sniff only — LI can't drive, so this board can never write to the airbag bus. |
| **B1** (`K2-A`) | U3 pin 6 (K, secondary channel) | OBD **pin 8** (10AS diagnostic bus) — bidirectional; needed to actually write requests to the 10AS (e.g. for an eventual EKA read), not just listen |
| **B2** (`K2-B`) | U3 pin 6 (K) — same node as B1, 2nd slot | spare slot on the 10AS node — not currently used |
| **B3** (`K2-RO`) | U3 pin 8 (LI) — read-only listen tap | **10AS→ECM mobilise line** (C225 pin 15 → C1017 pin 26) — **off the OBD2 pigtail entirely**, tapped via a direct splice at the bench. Per the 2026-09-28 PIO+DMA capture this line is DC-enable-like (no decodable serial), so the plain LI comparator read is sufficient for state monitoring. |
| **GND** | common ground | **not landed** — OBD pin 4 (chassis ground) deliberately left unconnected, see "Ground handling" below |
| **GND** | common ground | OBD pin 5 — Board 1's only ground reference |
| **12V** | fuse → TVS → {Vs, buck} | OBD pin 16 |

- **A1/A2 are ONE electrical node** (same for B1/B2) — whatever's landed on either
  is tied together permanently until a wire is physically moved. **A3/B3 are
  separate, read-only LI nodes**, isolated from the K nodes.
- **A1+A2 tied to pins 7+15 is a deliberate design choice for this build** — it
  keeps U2's 0xDA channel permanently open rather than optional/removable. To go
  back to plain OBD (no L↔K strap), unscrew the pin-15 wire from A2.
- **Why A3/B3 (both RO) ended up on SRS and the immobiliser mobilise line
  specifically:** there are only 2 bidirectional channels (K1, K2), already
  committed to the engine (0xDA) and the 10AS. SRS and the mobilise line only
  need passive state/traffic visibility here, not write access — and for the
  mobilise line in particular, read-only is a genuine safety property (this
  board can never accidentally assert/deassert the real mobilise signal),
  not just a resource-allocation leftover.
- LO (U2 pin 2 / U3 pin 2) is **not** a terminal — it's a fixed internal wire
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

### Ground handling — pin 5 ONLY, pin 4 deliberately not landed (CORRECTED 2026-10-20)

**J1962 pins 4 and 5 are two different grounds by spec:** pin 4 = **chassis
ground** (shared with everything else on the vehicle — starter, alternator,
lights — can carry noise and real transient current); pin 5 = **signal
ground**, meant as a dedicated, cleaner reference specifically for diagnostic
electronics.

**Earlier decision (2026-09-29) was to bond pins 4 and 5 together, reasoning
that "they're probably already bonded near the connector anyway" and that our
low-current circuit wouldn't care. Both parts of that turned out wrong:**

- **They're not already bonded near the connector on this vehicle.** Per RAVE
  (`docs/dlc-pinouts.md`), pin 4 goes to splice **S204/E201** and pin 5 goes to
  splice **E200** — two genuinely distinct ground returns in the real harness,
  not a shared local junction.
- **The risk isn't Board 1's own current draw — it's current we'd divert from
  elsewhere.** Board 1 is an *external* device plugged into an already-wired,
  already-grounded vehicle. Bonding pins 4 and 5 on Board 1 creates a brand-new
  parallel current path between two ground networks the OEM deliberately kept
  separate. Under load (starter cranking, alternator ripple), some of that
  chassis-ground current could divert through Board 1's thin, signal-rated
  pigtail wiring and ground pour — wiring never sized for chassis-ground duty —
  and in doing so inject exactly the noise pin 5 exists to avoid.

**Fix: ground Board 1 through pin 5 only.** Pin 4 is **not landed on either
GND terminal** — it's simply left unconnected, same treatment as any other
unused OBD pin. The second physical GND terminal slot still exists on the
9-terminal block and is still the same internal GND net as the first (it's one
node, not two), but nothing is screwed into it unless a future need arises.
This way Board 1 never bridges the two ground networks, and the vehicle's own
(OEM-designed) grounding scheme continues to handle chassis-ground duty
exactly as intended — Board 1 just rides along on the clean reference pin 5
was built for.

(The ground-pour / single-plane via reasoning below still applies to *how*
pin 5 reaches every other ground point on the board — U2/U3 GND, the buck,
the Pico — it's just that pin 4 is no longer one of the things tying into
that plane.)

### PCB layer strategy — 2 layers, ground pour + zoned placement (2026-09-29)

Board 1 is a **2-layer board** (per `hardware/gems-2pcb/README.md` fab spec — 2
layers is plenty here). True per-signal-type layer separation (a dedicated power
plane, a dedicated ground plane, separate signal layers) needs 4+ layers and is
overkill for this design. The 2-layer approach instead separates by **plane +
placement**:

- **Bottom layer = one continuous ground pour.** Every GND pin (both chips, buck,
  Pico, the star point above) drops a via straight into this pour. Gives a
  low-impedance return path for every signal and a de facto shield under the
  top-side traces — this is the single highest-value thing a 2-layer board can do.
- **Top layer = components + traces, separated by PHYSICAL ZONE, not by layer:**
  - **Power zone** — F1 (fuse), D1 (TVS), the buck, D2 (1N5817) — clustered
    together, 12 V/5 V traces sized for current (≥1.5 mm / a pour, not hair-thin).
  - **Signal zone** — U2/U3 (L9637D) K/L/LI lines and their UART traces to the
    Pico — kept short, and **physically away from the power zone**, especially
    away from the buck's switching node (switching regulators radiate noise right
    at that node — a classic glitch source for a nearby UART/K-line receiver).
  - **RF keep-out** — nothing routed on either layer under or near the Pico
    2 W's antenna end.
  - **Star ground** (above) sits between the two zones, close to the ground-pour
    via field, not buried inside the noisy power zone.
- **Net class widths** (carried over from the original single-transceiver spec,
  now applying per-transceiver): power ≥ 1.5 mm / pour; K/L ≥ 0.4 mm; UART/Vcc
  ≥ 0.3 mm; 0.2 mm min clearance (JLC handles this easily).

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

### DUAL transceiver — U2 + U3, two K-line channels (DECIDED 2026-09-28)

Board 1 now carries **TWO L9637D transceivers** so it can drive **two independent
K-line channels at once** — engine on one, a second module (10AS / EAS / SRS) on the
other — with **independent baud** (engine 10400, 10AS 9600) on the RP2040's two
hardware UARTs. This is what the immobiliser relearn wants (ECM learn session live
on U2 *while* commanding the 10AS on U3) and what multi-line vehicles need (P38
engine on pin 7 *and* EAS on 11/12 concurrently). **U1 = Pico** (host MCU), driving
both channels.

| | **U2 — K-line #1 (engine)** | **U3 — K-line #2 (10AS/EAS/SRS)** |
|---|---|---|
| UART | **UART0 / `Serial1`** | **UART1 / `Serial2`** |
| TX (4) | Pico (U1) **GP0** | Pico (U1) **GP4** (`Serial2.setTX(4)`) |
| RX (1) | Pico (U1) **GP1** | Pico (U1) **GP5** (`Serial2.setRX(5)`) |
| LO (2) | Pico (U1) **GP2** (fixed wire, not a terminal) | Pico (U1) **GP6** (fixed wire, not a terminal) |
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
  (0 = U2/Serial1, 1 = U3/Serial2 at its own baud) to the K-line commands
  (`CMD_INIT` / `CMD_SEND_RECV` / `CMD_RAW_XFER` / `CMD_MONITOR_L` / `CMD_CAPTURE`),
  mirroring the existing Serial1 handlers onto Serial2.

### On-car power — OBD 12 V powers the Pico (route A, DECIDED 2026-09-28)

Board 1 is **self-powered on a running truck** — no separate 5 V brick. USB is now
**optional** (data/flashing only).

```
OBD pin 16 (+12 V) ─[F1 1A]─┬─[TVS 1.5KE24A]─► U2 Vs + U3 Vs
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

### ⚠️ Terminal scheme CORRECTED 2026-10-05 — Board 2 is now a two-layer design; Board 1 is unaffected

Decided 2026-10-05: **Board 1 stays exactly as documented above (9 terminals,
unchanged).** Only **Board 2** changes, to a deliberate two-layer scheme that
reduces the number of "things that move" to one consistent place on this board:

1. **Fixed layer (soldered, never moves):** the female J1962 pigtail's 16 wires
   are **soldered directly** to a **16-position pad block** on Board 2, one pad
   per OBD pin number (P2.1 … P2.16), always in the same place. This is a
   permanent, mechanically durable connection — no thin pigtail wire gets
   repeatedly screwed/unscrewed.
2. **Patch layer (screwed, the actual reconfiguration point):** a separate screw
   terminal block sits between the fixed 16-pad block and the bench-module
   terminal blocks (`TB-ECU`, `TB-10AS`, and any future module block). **All
   reconfiguration on Board 2 happens here** — move a jumper from a P2.n pad to
   whichever module terminal needs that OBD line this session.

This supersedes the single-layer `TB-ECU`/`TB-10AS` wiring below only in that the
**P2→TB nets are no longer a fixed hard-wire** — they now route through the patch
layer. The module-side terminal blocks (`TB-ECU`, `TB-10AS`) and their targets are
unchanged.

### Parts
| Ref | Part | Notes |
|---|---|---|
| P2 | **female J1962 pigtail**, wires **soldered** to a 16-position pad block | receives Board 1; **fixed/permanent**, one pad per OBD pin (P2.1…P2.16) — not a screw terminal |
| PATCH | screw terminal block (patch layer) | routes selected P2.n pads to `TB-ECU` / `TB-10AS` / future module blocks; **this is where wires move** |
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

V12S ── P2.16 (fixed pad)             (+12 up to Board 1 / L9637D Vs)
V12S ── TB-ECU:+12main                (ECU C1033 pin 7)
V12S ── SW2 ── TB-ECU:+12ign          (ECU C1033 pin 8)
V12S ── TB-10AS:+12  (×2)             (10AS C225 pin 25 AND pin 10 — feed both)

P2.7  (fixed pad, K1/U2) ──PATCH── TB-ECU:K    (ECU C1017 p23)
P2.8  (fixed pad, K2/U3) ──PATCH── TB-10AS:K   (10AS C225 p17)
                                       [K1 and K2 stay SEPARATE through the patch
                                        layer — never jumper them together. This
                                        is what fixes the earlier draft that
                                        shared both onto pin 7, which recreated
                                        the shared-node contention.]
P2.15 (fixed pad, L) ──PATCH── TB-ECU:L        (ECU C1017 p20 only — 10AS has no L)

GND (J2−) ── P2.4 ── P2.5 (fixed pads) ──PATCH──
             TB-ECU:GND (ECU C1033 p5/p9/p10/p16) ──
             TB-10AS:GND (10AS C274 p11)                                  [star ground]
```

**The other ~10 pads on the 16-position block** (P2.1, P2.2, P2.3, P2.6, P2.9,
P2.11, P2.12, P2.13, P2.14 — incl. CAN 6/14, J1850 2/10) **sit soldered and idle**,
unpatched, exactly mirroring Board 1's unused-pin handling. Patch them later if a
future module needs one — no resoldering of the pigtail required.

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
| K1 (engine, U2) | Board 1 ↔ car ECU (OBD pin 7) | Board 1 ↔ Board 2 → ECU C1017 p23 |
| K2 (secondary, U3) | Board 1 ↔ car pin 8 module | Board 1 ↔ Board 2 → 10AS C225 p17 — **separate from K1**, never bridged |
| L-line | Board 1 terminal A2↔K, OBD pin 15 → car | Board 1 terminal A2↔K, OBD pin 15 → Board 2 → ECU C1017 p20 |
| GND | car OBD pin 4/5 | DC adapter → Board 2 → OBD pin 4/5 + ECU + 10AS |
| U1 (Pico) power | buck → VSYS (route A), USB optional (data/flashing) | same — buck fed from Board 2's DC 12 V via the OBD pass-through |

**Power is inherently single-source:** Board 1 is *either* in the car *or* in
Board 2, so OBD pin 16 only ever has one 12 V origin. Never power the bench from
the DC adapter while Board 1 is also in a car.

## Build / safety checklist
1. **Connector genders:** Board 1 male, Board 2 female. Board 2's pigtail is
   **soldered** to its 16-pad block (fixed); reconfiguration on Board 2 happens
   at the **patch screw layer** between that pad block and `TB-ECU`/`TB-10AS`,
   not by moving the pigtail itself.
2. **L9637D pin-1 orientation** confirmed before any power; **Vcc = 3.3 V**.
3. **Terminal A2 landed** (OBD pin 15 on the K1/U2 node) for bench/proprietary
   (0xDA) work; unland it for plain car OBD only.
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
