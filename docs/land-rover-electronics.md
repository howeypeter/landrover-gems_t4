# Late-1990s Land Rover electronics reference

Representative vehicle: **P38 Range Rover 4.0/4.6 V8 with GEMS engine
management (1995–1998)** — the user's own vehicle type and the research focus
of this project. The Discovery 2 material that previously led this document is
retained below as an era variation.

Diagrams: `../diagrams/d2-kline-diagnostic-network.svg` and
`../diagrams/d2-module-hardwired-links.svg` still show the Discovery 2
topology — P38 versions are a pending task.

## GEMS engine management

- **GEMS** ("Generic Engine Management System") is a **Lucas/Sagem** engine
  management system fitted to the **Rover V8 4.0 and 4.6** in the P38 Range
  Rover from launch until the **1999 model year**, when it was replaced by
  **Bosch Motronic M5.2.1** (the "Thor" engine — new manifold, returnless
  fuel). "Do I have GEMS or Thor?" is the first fork in every P38 engine
  procedure.
- Single ECM handles **fuel and ignition** together: hot-wire mass airflow
  metering and **distributorless wasted-spark ignition** via coil packs — a
  generation beyond the Discovery 1 / Classic's Lucas 14CUX (fuel-only, with
  a distributor).
- **OBD-II**: North American spec GEMS trucks are genuinely OBD-II compliant
  over ISO 9141-2 — a generic scanner gets emissions data. The TestBook gets
  much more: full fault codes, live data, actuator drives, and adaptations
  over the same K-line.
- **Immobilisation**: the ECM will not run the engine until it receives a
  coded mobilisation signal from the **BeCM**. A BeCM/ECM sync fault gives
  the infamous "ENGINE IMMOBILISED" message — a party-piece failure mode
  worth emulating.
- Authoritative service source: the **RAVE manual/CD** (official Land Rover
  workshop documentation) covers GEMS diagnostics, pinouts, and fault codes.

## The headline fact: no CAN bus

A late-90s Land Rover has **no CAN bus at all**. Every diagnosable ECU is
reached over a single shared diagnostic wire — the **ISO 9141 "K-line" on
pin 7 of the J1962 OBD socket** — at about **10.4 kbit/s**, half-duplex,
tester-initiated. The TestBook addresses each module individually over that
one wire. It is a star for diagnostics only; the modules do not talk to each
other over it. CAN only reaches Land Rover with the BMW-engineered **L322
Range Rover in 2002**.

## The computers on board (GEMS P38 Range Rover)

| Module | Role | On K-line? |
|---|---|---|
| GEMS ECM | 4.0/4.6 V8 fuel + ignition (Lucas/Sagem) | yes |
| EAT ECU | ZF 4HP24 automatic gearbox | yes |
| ABS ECU | Wabco ABS + electronic traction control | yes |
| EAS ECU | Electronic air suspension: height sensors, compressor, valve block | yes |
| BeCM | Body electrical Control Module — the P38's defining feature (see below) | yes |
| HEVAC ECU | Climate control (blend motors; shows the "book symbol" when it logs faults) | yes |
| SRS ECU | Airbags | yes |
| Instrument pack / message centre | Gauges + the text message centre ("EAS FAULT", "SLOW 35 MPH") | via BeCM serial link |

(Diagnostic addresses are representative in the emulator; exact values vary
by market and year.)

## The BeCM: the P38's central nervous system

Where the Discovery 2 splits body control between a BCU and an engine-bay
IDM, the P38 concentrates nearly everything in the **BeCM**, a large body
computer under the driver's seat:

- Runs locks, alarm, immobiliser, lighting, wipers, windows (via door
  **outstations** on serial links), and most relay functions directly.
- Drives the **instrument pack and message centre over a serial datalink** —
  many warnings the driver sees are BeCM messages, not hardwired lamps.
- Sends the **coded mobilisation signal to the GEMS ECM** — no code, no
  start.
- Notorious failure modes: refusing to **sleep** (flattening the battery),
  and BeCM/ECM immobiliser sync faults.

## How modules coordinate while driving

Still no bus chatter — dedicated wires and slow proprietary serial links:

- **BeCM ↔ instrument pack**: serial datalink carrying gauge data and
  message-centre text.
- **BeCM → GEMS ECM**: coded immobiliser mobilisation signal.
- **BeCM ↔ door outstations**: serial links for windows/locks/switches.
- **EAT ↔ GEMS ECM**: torque reduction request during shifts.
- **ABS → ECM/instruments**: hardwired road-speed pulse signal.
- **EAS ECU → message centre (via BeCM)**: fault and height-mode messages.
- Everything else is plain analogue or switched 12V.

**Result**: every system is an island. The virtual transport should model
"one K-line, tester polls each ECU by address," and the vehicle-configuration
step matters because there is no gateway module and no network discovery.

## OBD-II is only half-true

- **Petrol V8s** (especially NAS trucks) are OBD-II compliant for emissions
  data over ISO 9141-2.
- **Everything else on the truck** — EAS, BeCM, ABS, HEVAC, SRS — speaks
  proprietary Rover/Lucas protocols on the same K-line. This is precisely why
  a TestBook was needed and why a generic ELM327 sees almost nothing beyond
  the engine.

## Era variations

- **Discovery 2 (1998+)**: Td5 diesel (proprietary, not OBD-II) or Bosch
  Motronic V8 (never GEMS). Distributed body control (BCU + IDM) instead of
  a BeCM; adds SLABS (ABS + self-levelling), ACE (active cornering). The
  existing `d2-*` diagrams show this truck.
- **Range Rover Classic / Discovery 1 V8**: Lucas **14CUX** fuel-only
  injection with a distributor — the generation before GEMS.
- **Freelander 1** (1997+): same no-CAN, K-line-star pattern with fewer
  modules.
- **Defender**: barely computerized until the Td5 engine (1998) brought an
  ECM.

## Consequences for the T4 emulator

- The virtual transport models **"one K-line, tester polls each ECU by
  address"** rather than a bus full of chatter.
- The vehicle-ID step should land on a **GEMS-era P38** (VIN decode →
  4.0/4.6 GEMS vs Thor fork is authentic and matters).
- P38-flavoured party pieces: **EAS height/calibration screens**, **BeCM
  settings and immobiliser sync**, message-centre text mirroring faults.
- The four fault scenarios (healthy / coolant sensor / cylinder misfire /
  lambda heater) all fit a petrol V8 naturally — arguably better than the
  Td5, which has no lambda sensors.
- Authentic slowness: ISO 9141's tester-initiated ~10.4 kbit/s nature is why
  the real T4's "communicating with ECU… please wait" pauses were so long.
- **Protocol honesty note**: Andrew Revill's byte-level $61/$7f documentation
  is for **MEMS3** (Rover K-series). GEMS's exact wire protocol differs; the
  emulator uses T4-style request/response records as a faithful *stylization*
  unless/until GEMS-specific protocol documentation is found.
