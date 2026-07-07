---
name: research-gems-data
description: Research findings — GEMS fault codes, live data parameters, actuator tests, adaptations, coding, immobiliser
metadata:
  type: reference
---

# GEMS Diagnostic Data Catalog

Research pass 2026-07-06. P38A 4.0/4.6 GEMS (1994/95–1999).

## Two most authoritative public sources
1. **Nanocom "Lucas GEMS ECU Guide" PDF** — functional clone of the GEMS
   diagnostic feature set; documents live-data names, settings, output tests,
   adaptation resets, security-learn verbatim. Best public description of what
   the GEMS protocol exposes. https://www.nanocom-diagnostics.com/uploads/downloads/Lucas%20GEMS%20ECU%20Guide.pdf
2. **"Range Rover P38A V8 OBD Fault Codes"** from the 1999 Rover Workshop Manual
   — authoritative DTC list, split at "up-to-99MY (GEMS)" vs "99MY-up (Thor/Disco
   II)". Only the up-to-99MY block is GEMS.

**Structural insight for the emulator:** GEMS is a "settings page + live inputs +
on/off outputs + utility" model, NOT a PID browser. Build the UI around five
buckets: Read/Clear Faults · Settings (read/edit/write) · Inputs (live data, 3
tabs) · Outputs (actuator on/off) · Utility (learn + reset).

## Fault codes (DTCs)
- Format: 5-char P-codes (P0xxx generic + P1xxx manufacturer). ECU self-detects
  ~150 practical faults; stores ONE freeze-frame (overwritten by next).
- CAVEAT: P-code descriptions are how RAVE/TestBook *presented* faults; whether
  GEMS' K-line used those exact P-numbers or a raw index mapped to P-codes is
  undocumented [speculative]. Presenting P-codes is authentic to the experience.

Key GEMS DTC groups (all confirmed, up-to-99MY block):
- Crank/cam: P0335/P0336/P0340
- Throttle pot: P0121/P0122/P0123
- Coolant temp: P0116/P0117/P0118/P0125
- **Fuel temp (GEMS party piece)**: P0181/P0182/P0183
- Knock (bank A/B): P0326-P0328 / P0331-P0333
- Injectors: P0201-P0208 (circuit) + P1201-P1208 (open/ground short) per cyl
- IACV/idle: P0506/P0507 + P1508/P1509 (stepper open/short)
- O2 signal: P013x/P015x families (bank A/B, up/downstream)
- **O2 heaters (lambda-heater scenario maps here)**: P1185-P1190 upstream,
  P1191-P1196 downstream
- Fuel trims: P0171/P0174 lean, P0172/P0175 rich, P1171/P1172 both banks
- Catalyst: P0420/P0430
- EVAP (NAS): P1440, P0441/P0442/P0443/P0446/P0448/P0451-P0453/P1447
- Gearbox interface: P1775/P1776/P1777
- ECM/anti-theft: P0605, P1607, P1621, P1622/P1623, P1666-P1668, P1672-P1674
- **Misfire (misfire scenario)**: P0300/P1300 multi-cyl; P0301-P0308 /
  P1301-P1308 per-cylinder; P1319 misfire-with-low-fuel (distinctive GEMS).
  P1313/P1314 bank-level [lightly speculative].

**EXCLUDE from GEMS emulator (99MY-up Thor/Disco II, CAN-era, era-wrong):**
P0261-P0283, P1510/P1513/P1514/P1551-P1553, P0102/P0103, P1129, P0412-P0418,
P1230-P1232, P1535-P1538, P1590-P1592, P0600 "CAN time out."

## Live data (Inputs) — ~35 params in 3 tabs (fits the 40-60 gauge target)
**FUELLING:** Loop status (5-state enum), pre/post-cat O2 sensors, fuel trim
long/short, Adaptive FMFR (±0.625 limits), fuel temperature (fail-safe→40°C),
fuel level (inverted: 5V=empty), oxygen configuration.

**AIR & IDLE:** current throttle position (0.5-0.65V idle→5V at 5500rpm;
fail-safe limits 1740rpm), stored throttle position, adaptive air flow AMFR
(±5.5 Kg/Hr), current air flow (~mid-20s idle→200 at 5500), intake air temp
(fail-safe→50°C), MAF voltage, secondary air status, run line position, long/
short adaptive idle, idle speed reference, IACV stepper (15-30 steps warm idle,
range 0-200), engine RPM, gearbox retard (17%→100%), calculated load %, gearbox
status D/P.

**ENGINE-OTHERS:** coolant temp, battery V (**quirk: some ~1996 GEMS report
fixed 16V — candidate authentic bug to emulate**), road speed mph/kmh (from ABS
ECU), A/C request, front screen load, ignition switch, ABS volts (rough-terrain
misfire suppression), security learn status, security mobilized status, transfer
box V (NAS), ignition timing advance.

Refresh rate: no GEMS-specific figure found. K-line ~10.4kbit/s half-duplex
tester-polled → the fewer-gauges-faster tradeoff is physically authentic. Revill
MEMS3 figure (~20/s one measure → ~1 per 2s for 108) is a reasonable
stylization, but GEMS exposes ~35 named params, not 108.

## Actuator tests (Outputs) — simple on/off toggles
MIL (normal: ON ign-on, OFF engine-running) · O2 sensor heater · **fuel pump
relay** (the "Test not available — engine running" refusal belongs here) · A/C
grant (pin 1 big black connector 0↔5V) · condenser fan.

NOTE: documented GEMS outputs are relay/lamp-level only. Individual injector/coil
firing is NOT in the documented GEMS output set — an "injector pulse" test is a
reasonable stylization but flag internally as not-confirmed-for-GEMS. Per-test
refusal *messages* are speculative for GEMS.

## Adaptations / resets (Utility + editable Settings)
- **Reset all adaptive values**: clears stored closed-throttle position + adaptive
  AMFR (not short-term idle); forces relearn over drive cycles.
- Editable Settings: short-term idle steps (0-255), closed throttle V (~0.6),
  Adaptive FMFR (±0.625), Adaptive AMFR (±5.5); long-term idle reset-only.
- No separate "throttle adaptation"/"fuel trim reset" menu items — subsumed above.
- T4's −6°…+3° ignition trim + idle offset: [confirmed for T4 generally,
  speculative for GEMS specifically — Nanocom guide shows no timing-trim field].

## Coding / programming (Settings: read→edit→write-back)
| Setting | Writable? | Purpose |
|---|---|---|
| Security | Yes | Identity transfer to replacement ECU |
| Dealer ID | Yes | Part of identity transfer |
| VIN number | Yes | Last 6 digits |
| Build code | Yes | Build week/year |
| Transmission | Yes | Auto/Manual |
| Engine | Yes | 4.0/4.6 selection |
| Market | Read-only | Tune + O2 config |
| GEMS revision, Patented/Intel/TMS/Part/Tune ID | Read-only | Identity info |

Calibration/tune flashing (separate): TestBook could reflash GEMS tune by VIN;
forums say ECM reprogrammable ~16 times. But per hardware research this is
disputed — GEMS maps are EPROM; treat a "tune update by VIN" as a static
lookalike screen. (See [[research-gems-hardware]] — the two agents mildly
disagree on whether TestBook reflashed GEMS tune over the port; hardware agent
says no port reflash exists, data agent cites forum claims of VIN-based reflash.
Resolve toward: no real GEMS calibration flash — emulate as lookalike.)

## Immobiliser (GEMS ↔ BeCM) — the P38 defining behaviour
- On ignition-on, BeCM (if holding valid code, not alarmed) sends coded signal to
  GEMS; GEMS compares to stored code; match→start. Correct sync shown by orange
  check-engine light illuminating at ign-on (if it doesn't, not synced, won't
  start).
- Resync needed if GEMS/BeCM/lockset+fob replaced. Major cause of P38 non-starts.
- **Security Learn procedure**: tool puts GEMS in learn mode → next code stored
  as new master (not compared) → cycle ignition off/on → BeCM re-sends → GEMS
  validates & stores; any error → rejected, nothing stored (check via Security
  Learn input in Inputs→Others).
- Tools: TestBook/T4, Nanocom, Faultmate, Sync-Mate (<30s).
- **EKA (Emergency Key Access)**: BeCM stores a 4-digit code, entered by turning
  driver's door lock back-and-forth to match. BeCM function, NOT GEMS. (Exact
  keystroke sequence behind Tollbit block.)

## GEMS ECU pinout (for virtual harness / fault injection)
Coils as wasted-spark pairs — C1033: pin1=coils 5+8, pin13=2+3, pin14=1+6,
pin15=4+7. MIL on C1032 pin22. Fuel-pump relay C1032 pin24. Full tables in
Nanocom PDF pp2-3.

## Sources
- Nanocom Lucas GEMS ECU Guide: https://www.nanocom-diagnostics.com/uploads/downloads/Lucas%20GEMS%20ECU%20Guide.pdf
- Rover Manual P38A DTC list (rangerovers.net thread): https://www.rangerovers.net/threads/diagnostic-trouble-codes-land-rover-gems-p38-1994-1999.20287/
- troublecodes.net Land Rover: https://www.troublecodes.net/landrvr/
- Sync-Mate: https://rangeroverp38.org/becm-sync-mate-range-rover-p38-immobiliser-gems-ecu/

Related: [[research-gems-hardware]], [[research-kline-protocols]],
[[research-python-architecture]], [[gems-p38-focus]]
