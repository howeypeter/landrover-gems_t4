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
| 20 | Data Link Connector (OBD-II) — K/L line |
| 21 | Heated Front Screen |
| 23 | Data Link Connector (OBD-II) — K/L line |
| 26 | Theft Alarm Unit |
| 27 | Vehicle Speed Output (Instruments) |
| 28 | Air Conditioning Switches |
| 29 | Air Conditioning Switches |
| 30 | Fuel Pressure Sensor |
| 32 | Heated Oxygen Sensors |
| 33 | Right Heated Oxygen Sensor |
| 34 | Left Heated Oxygen Sensor |
| 35 | Engine Fuel Temperature Sensor |
| 36 | Multiple Sensor Connection |

> NAS K-line = pin 23, non-NAS (UK/Euro) = pin 20 (confirmed on hardware; see
> `memory/real-gems-protocol.md`).

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
