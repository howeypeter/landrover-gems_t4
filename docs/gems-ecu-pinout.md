# GEMS ECU connector pinout — AUTHORITATIVE

**This is the authoritative GEMS ECU pinout for this project.** When a pin
function is needed (actuator testing, sensor probing, bench wiring), use this
table — not guesses, and not the FlemcoDesign app.

**Source:** "Lucas Gems Engine Management ECU pinout", rangerovers.net forum
thread (Range Rover Mk II / P38 section), reproducing the **BlackBox Solutions
`SM001` LUCAS GEMS System Help file, v1.27**. User-provided PDF:
`C:\Users\howey\Downloads\Lucas Gems Engine Management ECU pinout _ Range Rovers Forum.pdf`
(fitment verified for P38 <1999, NAS Defender 4.0/4.6 <1998, Discovery V8 NAS,
Morgan 4.0/4.6 2000+).

⚠️ **Meter-verify power/ground pins before applying 12 V.** Pin *functions* are
from the source above; physical pin location must be read off the connector and
confirmed with a multimeter (see `diagrams/gems-bench-rig-wiring.html` and the
manual's safety callout). An earlier bench-rig note assumed `C1033` pin 7 = main
+12 V / pin 8 = ignition; this source instead lists C1033 pin 7 = MFI Load Relay,
pin 8 = Satellite Fuse Box 1 — **reconcile by meter before powering.**

## Connector legend

The source labels connectors `C1017 / C1032 / C1033`. Mapping to the physical
plugs (colours from the ECU + prior project docs; **inferred**, meter-verify):

The same three plugs carry **two different connector-code schemes**: the SM001
source (Discovery/Morgan-derived) uses `C1017/C1032/C1033`; the **P38 Range Rover
wiring uses `C5xx`**. Both name the same physical plug:

| Plug (physical) | SM001 code | P38 code | Role |
|---|---|---|---|
| **Red 36-way** | `C1017` | `C507` | Sensors / inputs / comms (OBD-II data link) |
| **Black 36-way** | `C1032` | `C505` | **Outputs / actuators** (injectors, relays, IACV, MIL) |
| **Black 18-way** | `C1033` | `C509` | Ignition coils, grounds, crank sensor, load relay |

So the **red plug = C1017 = C507**; the pin tables below use the SM001 codes.

> Only pins the source assigns are listed; unlisted pin numbers are unpopulated
> in the source table. A few low pins on C1017 (2–6) fell at a page break in the
> capture — treat as unlisted / meter-verify if needed.

## Modern mating plugs: TE Connectivity (AMP) Econoseal III, .070 series

Added 2026-11-17 from the user's research (an AI-assisted part list), then cross-checked by web search and an adversarial agent review the same day (corrections applied below). These are the modern equivalents of the harness-side plugs that mate with the ECU's three headers. **Treat every part number as a lead until you check it against TE's drawings and, ideally, the number printed on your own plug.**

| Plug (physical) | SM001 / P38 code | Housing | Locking plate | Check result |
|---|---|---|---|---|
| Red 36-way | C1017 / C507 | **`346189-5`** (TE: "36 WAY REC HSG ASSY RED"); the user-supplied `344111-5` has no listing anywhere | `344112-1` | Red housing number corrected 2026-11-17. Keying vs the black housing is **not published**; check TE drawings C_346189_B and 114-3040 |
| Black 36-way | C1032 / C505 | `344111-1` | `344112-1` | Housing confirmed (Econoseal III 070, 36-way, black, glass-filled polyamide, 180 deg exit; [TE](https://www.te.com/en/product-344111-1.html)) |
| Black 18-way | C1033 / C509 | `344106-1` | `344107-1` | Housing confirmed (RS). `344107-1` is a valid 18-way anti-backout plate, but TE marks it **"Do Not Use for New Design"** and unavailable; use distributor stock |

**`344112-1` resolved:** TE lists it as a white nylon 36-way **anti-backout lock plate** ([TE](https://www.te.com/en/product-344112-1.html)), not a seal. The earlier "cable seal" document could not be re-found; ignore it. TE shows it as not currently available, so use distributor stock.

**DECISION (user, 2026-11-17): use `345808-1` (tin) as the female pin/terminal for all three plugs.** **Problem found in review:** TE lists `345808-1` as 24-20 AWG (0.2-0.5 mm2), tin, F-crimp and **unsealed / not sealable** ([TE](https://www.te.com/en/product-345808-1.html)). It cannot take a wire seal, so it does not give a sealed Econoseal connection. It may suit a bench harness, but fit in the cavity and retention are unconfirmed. No source confirmed it is stocked at DigiKey or Mouser, and TE shows it as not currently available. The gold `344113-1` (18-14 AWG) is the confirmed sealable fallback.

**Shared terminals, seals and plugs:**

| Item | Part | Check result |
|---|---|---|
| Female socket terminal, gold | `344113-1` | Confirmed: Econoseal III receptacle, 0.64 mm tab, **18-14 AWG** (the source list said 20-14), 7 A ([TE](https://www.te.com/en/product-344113-1.html)) |
| Female socket terminal, tin | `345808-1` | Exists but **unsealed**, 24-20 AWG (see the decision above) |
| Do NOT use | `175104-2` | TE lists it as a gold AMP **MULTILOCK** receptacle, unsealed, 20-16 AWG; it is not tin and not an Econoseal III contact. ProWire's generic kit includes it, but whether it fits Econoseal III cavities is unverified |
| Wire seal | `347874-1` (CHOSEN 2026-11-17) | TE: green silicone seal for 1.6-2.4 mm insulation OD, 20-15 AWG ([TE](https://www.te.com/en/product-347874-1.html)). User note: it is the seal for Econoseal III .070 / Series J housings; `345791-1` is for standard Econoseal .070 Mark II and is **superseded** (TE), so do not use. The Series J / Mark II split is the user's note, not verified by me. Needs a sealable terminal (not `345808-1`) |
| Cavity plug (blank unused holes) | `172748-1` | Appears in ProWire's generic 36-way Econoseal kit as a sealing plug |

**Wire size note:** terminals and seals come in wire-size ranges. `344113-1` covers 18-14 AWG while `347874-1` covers 20-15 AWG, so the overlap is 18-15 AWG. Match the terminal and seal to your wire gauge.

**Crimping:** these are Econoseal-style terminals, not Dupont-style contacts. A Dupont/SN-28B crimper will not suit them, and a sealed terminal needs two crimps (conductor barrel and seal wings). RS and Waytek list a TE ratchet hand tool for "ECONOSEAL J-11 and .070 Series", 20-16 AWG; whether its number is 91582-1 or 91583-1 is unresolved, and `344113-1` (18-14 AWG) likely needs a different die. TE application specs 114-18022 and 114-3040 name the correct tooling but could not be read. `345808-1` lists applicator 2151105-1 and extraction tool 1-1579007-5. Generic open-barrel tools with wire and seal nests (e.g. Kent 30-16 AWG, Hozan P-706) are cheaper but not TE-specified.

**Not found:** an ECU-side confirmation that GEMS uses Econoseal III at all. The only direct lead is the Rover MEMS ECU, which uses a TE 344108 / 344111 Econoseal pair. Confirm against the plug on your ECU.

## C1017 — Red 36-way (sensors / inputs / comms)

| Pin | Function |
|----:|----------|
| 1 | Anti-Lock Brake System ECU |
| 7 | Fuel Level Sensor |
| 8 | Right Heated Oxygen Sensor (Post Catalyst) |
| 10 | Knock Sensors |
| 11 | Left Knock Sensor |
| 12 | Right Knock Sensor |
| 13 | Intake Air Temperature Sensor |
| 14 | Engine Coolant Temperature Sensor |
| **15** | **Throttle Position Sensor** |
| 16 | Mass Air Flow Sensor |
| 17 | Left Heated Oxygen Sensor (Post Catalyst) |
| 18 | Neutral Sense Diode |
| 20 | Data Link Connector (OBD-II) — **L-line** (RAVE `lj`: WK) |
| 21 | Heated Front Screen |
| 23 | Data Link Connector (OBD-II) — **K-line** (RAVE `lj`: WLG) |
| 26 | Theft Alarm Unit |
| 27 | Vehicle Speed Output — ⚠️ RAVE `lj` routes VSS to **C1032 p27**, not here; meter-verify |
| 28 | Air Conditioning Switches |
| 29 | Air Conditioning Switches |
| 30 | Fuel Pressure Sensor |
| 32 | Heated Oxygen Sensors |
| 33 | Right Heated Oxygen Sensor |
| 34 | Left Heated Oxygen Sensor |
| 35 | Engine Fuel Temperature Sensor |
| 36 | Multiple Sensor Connection |

> NAS K-line = pin 23, non-NAS (UK/Euro) = pin 20 (confirmed on hardware; see
> `memory/real-gems-protocol.md`). **RAVE `lj` (Disco-1) confirms C1017 p23=WLG=
> K-line and p20=WK=L-line** — see `docs/rave-cross-reference.md` for the full
> pin-by-pin cross-reference against this table (all sensor/switch pins matched).

## C1032 — Black 36-way (OUTPUTS / actuators) ← actuator testing lives here

| Pin | Function |
|----:|----------|
| 1 | Compressor Clutch Relay (coil) |
| 3 | Condenser Fan Relay (coil) |
| 6 | Evaporative Emission Canister Vent Seal Valve |
| 11 | Fuel Injectors |
| 13 | Fuel Injectors |
| 15 | Idle Air Control Valve |
| 16 | Idle Air Control Valve |
| 18 | Fuel Injectors |
| 19 | Evaporative Emission Canister Purge Valve |
| 21 | Heated Oxygen Sensors (heater) |
| **22** | **Malfunction Indicator Lamp (MIL) (Instruments)** |
| **24** | **Fuel Pump Relay (coil)** |
| 28 | Heated Oxygen Sensors (Post Catalyst) (heater) |
| 30 | Fuel Injectors |
| 32 | Fuel Injectors |
| 33 | Fuel Injectors |
| 34 | Idle Air Control Valve |
| 35 | Idle Air Control Valve |
| 36 | Fuel Injectors |

## C1033 — Black 18-way (ignition / ground / relays)

| Pin | Function |
|----:|----------|
| 1 | Ignition Coils (5+8) |
| 4 | Throttle Position Sensor |
| 5 | Ground Distribution |
| 7 | MFI Load Relay |
| 8 | Satellite Fuse Box 1 |
| 9 | Ground Distribution |
| 10 | Ground Distribution |
| 11 | Crankshaft Position Sensor |
| 12 | Crankshaft Position Sensor |
| 13 | Ignition Coils (2+3) |
| 14 | Ignition Coils (1+6) |
| 15 | Ignition Coils (4+7) |
| 16 | Ground Distribution |
| 17 | MFI Load Relay (coil) |

## Actuator quick-reference (for `bench/`-style `$31` routine testing)

The GEMS outputs the T4 could drive, per the SM001 help file, all land on
**C1032**. Meter these pins (continuity/voltage to ground) when firing a routine:

| Output | Meter at | SM001 test behaviour |
|---|---|---|
| **Fuel pump relay** | **C1032 pin 24** | toggles the fuel-pump relay on/off |
| MIL lamp | C1032 pin 22 | ON with ignition, cycles under test |
| A/C compressor clutch relay | C1032 pin 1 | needle swings 0↔5 V (per SM001, on "PIN 1 of the big black connector") |
| Condenser fan relay | C1032 pin 3 | toggles condenser-fan relay |
| O2 sensor heaters | C1032 pin 21 / 28 | voltage measurement, on/off |
| Injectors | C1032 pins 11/13/18/30/32/33/36 | brief pulse only |
| Idle Air Control Valve | C1032 pins 15/16/34/35 | stepper |

Note: the SM001 "big black connector, PIN 1" reference for the A/C grant matches
C1032 pin 1 here — corroborating that **C1032 is the black outputs plug**.

## Wire colours (Lucas code)

British/Lucas wiring uses a base colour plus an optional tracer stripe. A
**one-letter** code is a solid colour; a **two-letter** code is **base + tracer**
— the **first letter is the main colour, the second is the tracer**. So `YU` =
*yellow with a blue tracer*, `NG` = *brown with a green tracer*.

| Code | Colour | | Code | Colour |
|------|--------|-|------|--------|
| B | Black | | P | Purple |
| U | Blue | | R | Red |
| N | Brown | | S | Slate (grey) |
| G | Green | | W | White |
| K | Pink | | Y | Yellow |
| O | Orange | | LG | Light green |

## Wire colours — C1017 / C507 (Red 36-way)

Transcribed from the user's **C507 photo** (Range Rover 4.0/4.6, 36-way red).
The photo is low-resolution, and Lucas colours can differ **NAS vs non-NAS and by
year** — so **meter-verify before trusting**, especially the pin the throttle
signal is on.

| Pin | Code | Colour (described) | Function |
|----:|------|--------------------|----------|
| 15 | `YU` | yellow with blue tracer | **Throttle Position Sensor** |
| 20 | `WK` | white with pink tracer | **L-line** (RAVE `lj`) — not yet physically checked, meter-verify |
| 23 | `WLG` | white with light-green tracer | **K-line** (RAVE `lj`) — not yet physically checked, meter-verify |
| 26 | `B` (solid black, per visual check) | black | **Theft alarm / mobilise** (10AS C225 pin 15) — continuity to 10AS not yet checked |

> The remaining C507 colour codes are legible only in part on the supplied photo;
> rather than risk mis-transcribing an authoritative table, fill each row in as
> the wire is meter-confirmed. Every code expands via the legend above (first
> letter = main colour, second = tracer).

## Physical pinout — C1017 / C507 (Red 36-way)

36-way connector. The **male** view looks into the **ECU header pins**; the
**female** (plug / loom side) view is the **left–right mirror** of it, because the
two halves mate face-to-face. Blank cells are the connector's keying gaps, not
pins.

**MALE — looking into the ECU header:**

|  |  |  |  |  |  |  |  |  |  |  |  |  |
|--|--|--|--|--|--|--|--|--|--|--|--|--|
|    | 12 | 11 | 10 | 9  | 8  | 7  | 6  | 5  | 4  | 3  | 2  | 1  |
| 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 |    |
|    | 36 | 35 | 34 | 33 | 32 | 31 | 30 | 29 | 28 | 27 | 26 | 25 |

**FEMALE — looking into the plug (loom side), mirror of the above:**

|  |  |  |  |  |  |  |  |  |  |  |  |  |
|--|--|--|--|--|--|--|--|--|--|--|--|--|
| 1  | 2  | 3  | 4  | 5  | 6  | 7  | 8  | 9  | 10 | 11 | 12 |    |
|    | 24 | 23 | 22 | 21 | 20 | 19 | 18 | 17 | 16 | 15 | 14 | 13 |
| 25 | 26 | 27 | 28 | 29 | 30 | 31 | 32 | 33 | 34 | 35 | 36 |    |

**NULL — positions with no wire fitted**, per the SM001 function table above:
pins **2, 3, 4, 5, 6, 9, 19, 22, 24, 25, 31**. (A specific C507 loom — e.g. a NAS
Range Rover — may populate some of these, such as a cam-position or park/neutral
input; confirm against your own C507 photo / meter.)
